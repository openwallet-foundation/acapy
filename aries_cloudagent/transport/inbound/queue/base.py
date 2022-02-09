"""Base classes for the inbound queue module."""
from abc import ABC, abstractmethod
import asyncio
import logging

from ....core.profile import Profile
from ...error import BaseError


class BaseInboundQueue(ABC):
    """Base class for the inbound queue generic type."""

    def __init__(self, root_profile: Profile):
        """Initialize base queue type."""
        self.logger = logging.getLogger(__name__)

    def __str__(self):
        """Return string representation used in banner on startup."""
        return type(self).__name__

    async def __aenter__(self):
        """Async context manager enter."""
        await self.open()

    async def __aexit__(self, err_type, err_value, err_t):
        """Async context manager exit."""
        if err_type and err_type != asyncio.CancelledError:
            self.logger.exception("Exception in inbound queue")
        await self.close()

    async def start_queue(self):
        """Start the queue."""

    async def stop_queue(self):
        """Stop the queue."""

    async def open(self):
        """Start the queue."""

    async def close(self):
        """Stop the queue."""

    @abstractmethod
    async def receive_messages(
        self,
    ):
        """Receive and send message to internal message router."""


class InboundQueueConfigurationError(BaseError):
    """An error with the queue configuration."""

    def __init__(self, message):
        """Initialize the exception instance."""
        super().__init__(message)


class InboundQueueError(BaseError):
    """An error with the queue."""
