"""Base outbound transport."""

from abc import ABC, abstractmethod, abstractproperty

from .message import OutboundMessage
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
        pass

    @abstractmethod
    async def __aenter__(self):
        """Async context manager enter."""
        pass

    @abstractmethod
    async def __aexit__(self, *err):
        """Async context manager exit."""
        pass

    @abstractproperty
    def queue(self):
        """Accessor for queue."""
        pass

    @abstractmethod
    async def handle_message(self, message: OutboundMessage):
        """
        Handle message from queue.

        Args:
            message: `OutboundMessage` to send over transport implementation
        """
        pass

    async def start(self) -> None:
        """Start this transport."""
        async for message in self.queue:
            await self.handle_message(message)
