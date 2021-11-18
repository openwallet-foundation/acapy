"""Base classes for the queue module."""
from abc import ABC, abstractmethod
import asyncio
import logging
from typing import Union

from ....core.profile import Profile
from ...error import BaseError, TransportError


class BaseOutboundQueue(ABC):
    """Base class for the outbound queue generic type."""

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
            self.logger.exception("Exception in outbound queue")
        await self.close()

    async def start(self):
        """Start the queue."""

    async def stop(self):
        """Stop the queue."""

    async def open(self):
        """Start the queue."""

    async def close(self):
        """Stop the queue."""

    @abstractmethod
    async def enqueue_message(
        self,
        payload: Union[str, bytes],
        endpoint: str,
    ):
        """Prepare and send message to external queue."""


class OutboundQueueError(TransportError):
    """Generic outbound transport error."""


class OutboundQueueConfigurationError(BaseError):
    """An error with the queue configuration."""

    def __init__(self, message):
        """Initialize the exception instance."""
        super().__init__(message)
