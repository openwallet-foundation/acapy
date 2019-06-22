"""Abstract outbound queue."""

from abc import ABC, abstractmethod


class BaseOutboundMessageQueue(ABC):
    """Abstract outbound queue class."""

    @abstractmethod
    async def enqueue(self, message):
        """
        Enqueue a message.

        Args:
            message: The message to send
        """

    @abstractmethod
    async def dequeue(self, timeout: int = None):
        """Get a message off the queue."""

    @abstractmethod
    async def join(self):
        """Wait for the queue to empty."""

    @abstractmethod
    def stop(self):
        """Cancel active iteration of the queue."""

    @abstractmethod
    def reset(self):
        """Empty the queue and reset the stop event."""

    @abstractmethod
    def __aiter__(self):
        """Async iterator magic method."""

    @abstractmethod
    async def __anext__(self):
        """Async iterator magic method."""
