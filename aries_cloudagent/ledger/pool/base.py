"""Ledger pool base class."""

from abc import ABC, ABCMeta, abstractmethod


class BaseLedgerPool(ABC, metaclass=ABCMeta):
    """Abstract ledger pool interface."""

    POOL_TYPE = None

    async def __aenter__(self) -> "BaseLedgerPool":
        """
        Context manager entry.

        Returns:
            The current instance

        """
        return self

    async def __aexit__(self, exc_type, exc, tb):
        """Context manager exit."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Accessor for the pool name."""

    @property
    @abstractmethod
    def type(self) -> str:
        """Accessor for the pool type."""

    @property
    def handle(self):
        """
        Get internal pool reference.

        Returns:
            Defaults to None

        """
        return None

    @property
    @abstractmethod
    def opened(self) -> bool:
        """Check whether pool is currently open."""
