"""Base outbound transport."""

from abc import ABC, abstractmethod
import asyncio

from ...error import BaseError
from ...messaging.outbound_message import OutboundMessage
from ...stats import Collector


class BaseOutboundTransport(ABC):
    """Base outbound transport class."""

    def __init__(self) -> None:
        """Initialize a `BaseOutboundTransport` instance."""
        self._collector = None

    @property
    def collector(self) -> Collector:
        """Accessor for the stats collector instance."""
        return self._collector

    @collector.setter
    def collector(self, coll: Collector):
        """Assign a new stats collector instance."""
        self._collector = coll

    async def __aenter__(self):
        """Async context manager enter."""
        await self.start()

    async def __aexit__(self, err_type, err_value, err_t):
        """Async context manager exit."""
        if err_type and err_type != asyncio.CancelledError:
            self.logger.exception("Exception in outbound transport")
        await self.stop()

    @abstractmethod
    async def start(self):
        """Start the transport."""

    @abstractmethod
    async def stop(self):
        """Shut down the transport."""

    @abstractmethod
    async def handle_message(self, message: OutboundMessage):
        """
        Handle message from queue.

        Args:
            message: `OutboundMessage` to send over transport implementation
        """


class OutboundTransportRegistrationError(BaseError):
    """Outbound transport registration error."""
