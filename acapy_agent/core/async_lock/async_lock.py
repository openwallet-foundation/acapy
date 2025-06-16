"""Abstract base class for an asynchronous lock service."""

from abc import ABC, abstractmethod
from typing import Optional


class AsyncLock(ABC):
    """Abstract base class for an asynchronous lock service."""

    @abstractmethod
    async def create(cls, connection_uri: Optional[str] = None):
        """Create an instance of the lock service."""
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    async def lock(self, value: str, timeout: float = 10.0) -> bool:
        """Acquire a lock with the given value."""
        raise NotImplementedError("Subclasses must implement this method.")
