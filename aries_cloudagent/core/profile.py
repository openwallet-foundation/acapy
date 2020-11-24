"""Classes for managing profile information within a request context."""

from abc import abstractmethod
from typing import Optional, Type, TypeVar

InjectType = TypeVar("Inject")


class Profile:
    """Base abstraction for handling identity-related state."""

    @property
    @abstractmethod
    def backend(self) -> str:
        """Accessor for the backend implementation name."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Accessor for the profile name."""

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

    def __repr__(self) -> str:
        """Get a human readable string."""
        return "<{}(backend={}, name={})>".format(
            self.__class__.__name__, self.backend, self.name
        )


class ProfileSession:
    """An active connection to the profile management backend."""

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

    @abstractmethod
    def inject(
        self, base_cls: Type[InjectType], required: bool = True
    ) -> Optional[InjectType]:
        """Get an instance of a defined interface base class tied to this session."""

    def __repr__(self) -> str:
        """Get a human readable string."""
        return "<{}(is_transaction={})>".format(
            self.__class__.__name__, self.is_transaction
        )
