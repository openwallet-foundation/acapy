"""Classes for managing profile information within a request context."""

from abc import abstractmethod
from typing import Mapping, Optional, Type

from ..config.injection_context import InjectionContext, InjectType


class Profile:
    """Base abstraction for handling identity-related state."""

    BACKEND_NAME = None
    DEFAULT_NAME = "default"

    def __init__(self, *, context: InjectionContext = None, name: str = None):
        """Initialize a base profile."""
        self._context = context or InjectionContext()
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
    def name(self) -> str:
        """Accessor for the profile name."""
        return self._name

    @abstractmethod
    async def start_session(self) -> "ProfileSession":
        """Start a new interactive session with no transaction support requested."""

    @abstractmethod
    async def start_transaction(self) -> "ProfileSession":
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
        required: bool = True
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

    def __repr__(self) -> str:
        """Get a human readable string."""
        return "<{}(backend={}, name={})>".format(
            self.__class__.__name__, self.backend, self.name
        )


class ProfileSession:
    """An active connection to the profile management backend."""

    def __init__(self, *, profile: Profile, context: InjectionContext = None):
        """Initialize a base profile session."""
        self._context = context or profile.context
        self._profile = profile

    @property
    def context(self) -> InjectionContext:
        """Accessor for the associated injection context."""
        return self._context

    @property
    def profile(self) -> Profile:
        """Accessor for the associated profile instance."""
        return self._profile

    @property
    def handle(self):
        """Get the internal session reference if supported by the backend."""
        return None

    @property
    def is_transaction(self) -> bool:
        """Check if the session supports commit and rollback operations."""
        return False

    def commit(self):
        """
        Commit any updates performed within the transaction.

        If the current session is not a transaction, then nothing is performed.
        """

    def rollback(self):
        """
        Roll back any updates performed within the transaction.

        If the current session is not a transaction, then nothing is performed.
        """

    def inject(
        self,
        base_cls: Type[InjectType],
        settings: Mapping[str, object] = None,
        *,
        required: bool = True
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

    def __repr__(self) -> str:
        """Get a human readable string."""
        return "<{}(is_transaction={})>".format(
            self.__class__.__name__, self.is_transaction
        )
