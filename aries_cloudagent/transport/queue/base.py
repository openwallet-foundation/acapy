"""Abstract message queue."""

from abc import ABC, abstractmethod
import asyncio


class BaseMessageQueue(ABC):
    """Abstract message queue class."""

    @abstractmethod
    async def enqueue(self, message):
        """
        Enqueue a message.

        Args:
            message: The message to add to the end of the queue

        Raises:
            asyncio.CancelledError if the queue has been stopped

        """

    @abstractmethod
    async def dequeue(self, *, timeout: int = None):
        """
        Dequeue a message.

        Returns:
            The dequeued message, or None if a timeout occurs

        Raises:
            asyncio.CancelledError if the queue has been stopped
            asyncio.TimeoutError if the timeout is reached

        """

    @abstractmethod
    async def join(self):
        """Wait for the queue to empty."""

    @abstractmethod
    def task_done(self):
        """Indicate that the current task is complete."""

    @abstractmethod
    def stop(self):
        """Cancel active iteration of the queue."""

    @abstractmethod
    def reset(self):
        """Empty the queue and reset the stop event."""

    def __aiter__(self):
        """Async iterator magic method."""
        return self

    async def __anext__(self):
        """Async iterator magic method."""
        try:
            message = await self.dequeue()
        except asyncio.CancelledError:
            raise StopAsyncIteration
        return message
