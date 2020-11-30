"""Classes for managing profile information within a request context."""

import logging

from abc import ABC, abstractmethod
from typing import Any, Mapping, Optional, Type

from ..config.base import ProviderError
from ..config.injector import BaseInjector, InjectType
from ..config.injection_context import InjectionContext
from ..config.provider import BaseProvider
from ..config.settings import BaseSettings
from ..utils.classloader import ClassLoader, ClassNotFoundError

from .error import ProfileSessionInactiveError

LOGGER = logging.getLogger(__name__)


class Profile(ABC):
    """Base abstraction for handling identity-related state."""

    BACKEND_NAME = None
    DEFAULT_NAME = "default"

    def __init__(self, *, context: InjectionContext = None, name: str = None):
        """Initialize a base profile."""
        self._context = context or InjectionContext()
        self._name = name or Profile.DEFAULT_NAME

    @property
    @classmethod
    def backend(cls) -> str:
        """Accessor for the backend implementation name."""
        return cls.BACKEND_NAME

    @property
    def context(self) -> InjectionContext:
        """Accessor for the injection context."""
        return self._context

    @property
    def name(self) -> str:
        """Accessor for the profile name."""
        return self._name

    @property
    def settings(self) -> BaseSettings:
        """Accessor for scope-specific settings."""
        return self._context.settings

    @abstractmethod
    def session(self, context: InjectionContext = None) -> "ProfileSession":
        """Start a new interactive session with no transaction support requested."""

    @abstractmethod
    def transaction(self, context: InjectionContext = None) -> "ProfileSession":
        """
        Start a new interactive session with commit and rollback support.

        If the current backend does not support transactions, then commit
        and rollback operations of the session will not have any effect.
        """

    def inject(
        self,
        base_cls: Type[InjectType],
        settings: Mapping[str, object] = None,
        *,
        required: bool = True,
    ) -> Optional[InjectType]:
        """
        Get the provided instance of a given class identifier.

        Args:
            cls: The base class to retrieve an instance of
            settings: An optional mapping providing configuration to the provider

        Returns:
            An instance of the base class, or None

        """
        return self._context.inject(base_cls, settings, required=required)

    async def close(self):
        """Close the profile instance."""

    def __repr__(self) -> str:
        """Get a human readable string."""
        return "<{}(backend={}, name={})>".format(
            self.__class__.__name__, self.backend, self.name
        )


class ProfileManager(ABC):
    """Handle provision and open for profile instances."""

    def __init__(self, context: InjectionContext = None):
        """Initialize the profile manager."""
        self.context = context or InjectionContext()

    @abstractmethod
    async def provision(self, config: Mapping[str, Any] = None) -> Profile:
        """Provision a new instance of a profile."""

    @abstractmethod
    async def open(self, config: Mapping[str, Any] = None) -> Profile:
        """Open an instance of an existing profile."""


class ProfileSession(ABC):
    """An active connection to the profile management backend."""

    def __init__(
        self,
        profile: Profile,
        *,
        context: InjectionContext = None,
        settings: Mapping[str, Any] = None,
    ):
        """Initialize a base profile session."""
        self._active = False
        self._context = context or profile.context.start_scope("session", settings)
        self._profile = profile

    async def _setup(self):
        """Create the session or transaction connection, if needed."""
        self._active = True

    async def _teardown(self, commit: bool = None):
        """Dispose of the session or transaction connection, if needed."""
        self._active = False

    def __await__(self):
        """
        Coroutine magic method.

        A session must be awaited or used as an async context manager.
        """

        async def init():
            if not self._active:
                await self._setup()
            return self

        return init().__await__()

    async def __aenter__(self):
        """Async context manager entry."""
        if not self._active:
            await self._setup()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._active:
            await self._teardown()

    @property
    def active(self) -> bool:
        """Accessor for the session active state."""
        return self._active

    @property
    def context(self) -> InjectionContext:
        """Accessor for the associated injection context."""
        return self._context

    @property
    def settings(self) -> BaseSettings:
        """Accessor for scope-specific settings."""
        return self._context.settings

    @property
    def handle(self):
        """Get the internal session reference if supported by the backend."""
        return None

    @property
    def is_transaction(self) -> bool:
        """Check if the session supports commit and rollback operations."""
        return False

    @property
    def profile(self) -> Profile:
        """Accessor for the associated profile instance."""
        return self._profile

    async def commit(self):
        """
        Commit any updates performed within the transaction.

        If the current session is not a transaction, then nothing is performed.
        """
        if not self._active:
            raise ProfileSessionInactiveError()
        await self._teardown(commit=True)

    async def rollback(self):
        """
        Roll back any updates performed within the transaction.

        If the current session is not a transaction, then nothing is performed.
        """
        if not self._active:
            raise ProfileSessionInactiveError()
        await self._teardown(commit=False)

    def inject(
        self,
        base_cls: Type[InjectType],
        settings: Mapping[str, object] = None,
        *,
        required: bool = True,
    ) -> Optional[InjectType]:
        """
        Get the provided instance of a given class identifier.

        Args:
            cls: The base class to retrieve an instance of
            settings: An optional mapping providing configuration to the provider

        Returns:
            An instance of the base class, or None

        """
        if not self._active:
            raise ProfileSessionInactiveError()
        return self._context.inject(base_cls, settings, required=required)

    def __repr__(self) -> str:
        """Get a human readable string."""
        return "<{}(active={}, is_transaction={})>".format(
            self.__class__.__name__, self._active, self.is_transaction
        )


class ProfileManagerProvider(BaseProvider):
    MANAGER_TYPES = {
        "in_memory": "aries_cloudagent.core.in_memory.InMemoryProfileManager",
        "indy": "aries_cloudagent.indy.sdk.profile.IndySdkProfileManager",
    }

    def __init__(self, context: InjectionContext):
        """Initialize the profile manager provider."""
        self._context = context
        self._inst = {}

    def provide(self, settings: BaseSettings, injector: BaseInjector):
        """Create the profile manager instance."""

        mgr_type = settings.get_value("wallet.type", default="in_memory").lower()
        if mgr_type == "basic":
            # map previous value
            mgr_type = "in_memory"

        # mgr_type may be a fully qualified class name
        mgr_class = self.MANAGER_TYPES.get(mgr_type, mgr_type)

        if mgr_class not in self._inst:
            LOGGER.info("Create profile manager: %s", mgr_type)
            try:
                self._inst[mgr_class] = ClassLoader.load_class(mgr_class)(self._context)
            except ClassNotFoundError as err:
                raise ProviderError(f"Unknown profile manager: {mgr_type}") from err

        return self._inst[mgr_class]
