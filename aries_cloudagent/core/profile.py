"""Classes for managing profile information within a request context."""

import logging

from abc import ABC, abstractmethod
from typing import Any, Mapping, Optional, Type

from .event_bus import EventBus, Event
from ..config.base import InjectionError
from ..config.injector import BaseInjector, InjectType
from ..config.injection_context import InjectionContext
from ..config.provider import BaseProvider
from ..config.settings import BaseSettings
from ..utils.classloader import ClassLoader, ClassNotFoundError

from .error import ProfileSessionInactiveError

LOGGER = logging.getLogger(__name__)


class Profile(ABC):
    """Base abstraction for handling identity-related state."""

    BACKEND_NAME: str = None
    DEFAULT_NAME: str = "default"

    def __init__(
        self,
        *,
        context: InjectionContext = None,
        name: str = None,
        created: bool = False,
    ):
        """Initialize a base profile."""
        self._context = context or InjectionContext()
        self._created = created
        self._name = name or Profile.DEFAULT_NAME

    @property
    def backend(self) -> str:
        """Accessor for the backend implementation name."""
        return self.__class__.BACKEND_NAME

    @property
    def context(self) -> InjectionContext:
        """Accessor for the injection context."""
        return self._context

    @property
    def created(self) -> bool:
        """Accessor for the created flag indicating a new profile."""
        return self._created

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
    ) -> InjectType:
        """
        Get the provided instance of a given class identifier.

        Args:
            cls: The base class to retrieve an instance of
            settings: An optional mapping providing configuration to the provider

        Returns:
            An instance of the base class, or None

        """
        return self._context.inject(base_cls, settings)

    def inject_or(
        self,
        base_cls: Type[InjectType],
        settings: Mapping[str, object] = None,
        default: Optional[InjectType] = None,
    ) -> Optional[InjectType]:
        """
        Get the provided instance of a given class identifier or default if not found.

        Args:
            base_cls: The base class to retrieve an instance of
            settings: An optional dict providing configuration to the provider
            default: default return value if no instance is found

        Returns:
            An instance of the base class, or None

        """
        return self._context.inject_or(base_cls, settings, default)

    async def close(self):
        """Close the profile instance."""

    async def remove(self):
        """Remove the profile."""

    async def notify(self, topic: str, payload: Any):
        """Signal an event."""
        event_bus = self.inject_or(EventBus)
        if event_bus:
            await event_bus.notify(self, Event(topic, payload))

    def __repr__(self) -> str:
        """Get a human readable string."""
        return "<{}(backend={}, name={})>".format(
            self.__class__.__name__, self.backend, self.name
        )


class ProfileManager(ABC):
    """Handle provision and open for profile instances."""

    def __init__(self):
        """Initialize the profile manager."""

    @abstractmethod
    async def provision(
        self, context: InjectionContext, config: Mapping[str, Any] = None
    ) -> Profile:
        """Provision a new instance of a profile."""

    @abstractmethod
    async def open(
        self, context: InjectionContext, config: Mapping[str, Any] = None
    ) -> Profile:
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
        self._awaited = False
        self._entered = 0
        self._context = (context or profile.context).start_scope("session", settings)
        self._profile = profile

    async def _setup(self):
        """Create the underlying session or transaction."""

    async def _teardown(self, commit: bool = None):
        """Dispose of the underlying session or transaction."""

    def __await__(self):
        """
        Coroutine magic method.

        A session must be awaited or used as an async context manager.
        """

        async def _init():
            if not self._active:
                await self._setup()
                self._active = True
            self._awaited = True
            return self

        return _init().__await__()

    async def __aenter__(self):
        """Async context manager entry."""
        if not self._active:
            await self._setup()
            self._active = True
        self._entered += 1
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        self._entered -= 1
        if not self._awaited and not self._entered:
            await self._teardown()
            self._active = False

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
        self._active = False

    async def rollback(self):
        """
        Roll back any updates performed within the transaction.

        If the current session is not a transaction, then nothing is performed.
        """
        if not self._active:
            raise ProfileSessionInactiveError()
        await self._teardown(commit=False)
        self._active = False

    def inject(
        self,
        base_cls: Type[InjectType],
        settings: Mapping[str, object] = None,
    ) -> InjectType:
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
        return self._context.inject(base_cls, settings)

    def inject_or(
        self,
        base_cls: Type[InjectType],
        settings: Mapping[str, object] = None,
        default: Optional[InjectType] = None,
    ) -> Optional[InjectType]:
        """
        Get the provided instance of a given class identifier or default if not found.

        Args:
            base_cls: The base class to retrieve an instance of
            settings: An optional dict providing configuration to the provider
            default: default return value if no instance is found

        Returns:
            An instance of the base class, or None

        """
        if not self._active:
            raise ProfileSessionInactiveError()
        return self._context.inject_or(base_cls, settings, default)

    def __repr__(self) -> str:
        """Get a human readable string."""
        return "<{}(active={}, is_transaction={})>".format(
            self.__class__.__name__, self._active, self.is_transaction
        )


class ProfileManagerProvider(BaseProvider):
    """The standard profile manager provider which keys off the selected wallet type."""

    MANAGER_TYPES = {
        "askar": "aries_cloudagent.askar.profile.AskarProfileManager",
        "in_memory": "aries_cloudagent.core.in_memory.InMemoryProfileManager",
        "indy": "aries_cloudagent.indy.sdk.profile.IndySdkProfileManager",
    }

    def __init__(self):
        """Initialize the profile manager provider."""
        self._inst = {}

    def provide(self, settings: BaseSettings, injector: BaseInjector):
        """Create the profile manager instance."""
        mgr_type = settings.get_value("wallet.type", default="in_memory")

        if mgr_type.lower() == "basic":
            # map previous value
            mgr_type = "in_memory"

        # mgr_type may be a fully qualified class name
        mgr_class = self.MANAGER_TYPES.get(mgr_type.lower(), mgr_type)

        if mgr_class not in self._inst:
            LOGGER.info("Create profile manager: %s", mgr_type)
            try:
                self._inst[mgr_class] = ClassLoader.load_class(mgr_class)()
            except ClassNotFoundError as err:
                raise InjectionError(f"Unknown profile manager: {mgr_type}") from err

        return self._inst[mgr_class]
