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
        pass

    @abstractmethod
    async def dequeue(self):
        """Get a message off the queue."""
        pass

    @abstractmethod
    def __aiter__(self):
        """Async iterator magic method."""
        pass

    @abstractmethod
    async def __anext__(self):
        """Async iterator magic method."""
        pass
