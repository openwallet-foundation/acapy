"""Basic in memory queue."""

import asyncio
import logging

from .base import BaseOutboundMessageQueue


class BasicOutboundMessageQueue(BaseOutboundMessageQueue):
    """Basic in memory queue implementation class."""

    def __init__(self):
        """Initialize a `BasicOutboundMessageQueue` instance."""
        self.queue = self.make_queue()
        self.logger = logging.getLogger(__name__)
        self.stop_event = asyncio.Event()

    def make_queue(self):
        """Create the queue instance."""
        return asyncio.Queue()

    async def enqueue(self, message):
        """
        Enqueue a message.

        Args:
            message: The message to add to the end of the queue

        Raises:
            asyncio.CancelledError if the queue has been stopped

        """
        if self.stop_event.is_set():
            raise asyncio.CancelledError
        self.logger.debug(f"Enqueuing message: {message}")
        await self.queue.put(message)

    async def dequeue(self, *, timeout: int = None):
        """
        Dequeue a message.

        Returns:
            The dequeued message, or None if a timeout occurs

        Raises:
            asyncio.CancelledError if the queue has been stopped
            asyncio.TimeoutError if the timeout is reached

        """
        if not self.stop_event.is_set():
            stopped = asyncio.ensure_future(self.stop_event.wait())
            dequeued = asyncio.ensure_future(self.queue.get())
            done, pending = await asyncio.wait(
                (stopped, dequeued),
                timeout=timeout,
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                if not task.done():
                    task.cancel()
            if dequeued.done():
                if dequeued.exception():
                    raise dequeued.exception()
                message = dequeued.result()
                self.logger.debug(f"Dequeuing message: {message}")
                return message
            elif not stopped.done():
                raise asyncio.TimeoutError

        if self.stop_event.is_set():
            raise asyncio.CancelledError

        return None

    async def join(self):
        """Wait for the queue to empty."""
        await self.queue.join()

    def task_done(self):
        """Indicate that the current task is complete."""
        self.queue.task_done()

    def stop(self):
        """Cancel active iteration of the queue."""
        self.stop_event.set()

    def reset(self):
        """Empty the queue and reset the stop event."""
        self.stop()
        self.queue = self.make_queue()
        self.stop_event.clear()
