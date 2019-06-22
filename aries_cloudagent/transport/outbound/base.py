"""Base outbound transport."""

from abc import ABC, abstractmethod

from ...error import BaseError
from ...messaging.outbound_message import OutboundMessage
from ...task_processor import TaskProcessor

from .queue.base import BaseOutboundMessageQueue


class BaseOutboundTransport(ABC):
    """Base outbound transport class."""

    @abstractmethod
    def __init__(self, queue: BaseOutboundMessageQueue) -> None:
        """
        Initialize a `BaseOutboundTransport` instance.

        Args:
            queue: `BaseOutboundMessageQueue` to use

        """
        self._queue = queue
        self._processor: TaskProcessor = None

    @abstractmethod
    async def __aenter__(self):
        """Async context manager enter."""

    @abstractmethod
    async def __aexit__(self, *err):
        """Async context manager exit."""

    @property
    def queue(self):
        """Accessor for queue."""
        return self._queue

    @abstractmethod
    async def handle_message(self, message: OutboundMessage):
        """
        Handle message from queue.

        Args:
            message: `OutboundMessage` to send over transport implementation
        """

    async def start(self) -> None:
        """Start this transport."""
        self._processor = TaskProcessor(max_pending=5)
        async for message in self.queue:
            await self._processor.run_retry(
                lambda pending: self.handle_message(message),
                retries=5,
                retry_delay=10.0,
            )
            self.queue.task_done()

    async def stop(self, wait: bool = True) -> None:
        """Stop the transport and clear the processor."""
        if wait:
            await self.queue.join()
            if self._processor:
                await self._processor.wait_done()
        self.queue.stop()

    async def enqueue(self, message: OutboundMessage):
        """
        Add a message to the queue.

        Args:
            message: `OutboundMessage` to send over transport implementation

        """
        return await self.queue.enqueue(message)


class OutboundTransportRegistrationError(BaseError):
    """Outbound transport registration error."""
