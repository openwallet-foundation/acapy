"""Basic in memory queue."""

import logging

from asyncio import Queue

from .base import BaseOutboundMessageQueue


class BasicOutboundMessageQueue(BaseOutboundMessageQueue):
    """Basic in memory queue implementation class."""

    def __init__(self):
        """Initialize a `BasicOutboundMessageQueue` instance."""
        self.queue = Queue()
        self.logger = logging.getLogger(__name__)

    async def enqueue(self, message):
        """
        Enqueue a message.

        Args:
            message: The message to send

        """
        self.logger.debug(f"Enqueuing message: {message}")
        await self.queue.put(message)

    async def dequeue(self):
        """
        Dequeue a message.

        Returns:
            The dequeued message

        """
        message = await self.queue.get()
        self.logger.debug(f"Dequeuing message: {message}")
        return message

    def __aiter__(self):
        """Async iterator magic method."""
        return self

    async def __anext__(self):
        """Async iterator magic method."""
        message = await self.dequeue()
        return message
