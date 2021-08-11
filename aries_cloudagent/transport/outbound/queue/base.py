"""Base classes for the queue module."""
from abc import ABC, abstractmethod
import logging
import asyncio
from typing import Union

from ...error import TransportError, BaseError
from ....config.settings import Settings


class BaseOutboundQueue(ABC):
    """Base class for the outbound queue generic type."""

    def __init__(self, settings: Settings):
        """Initialize base queue type."""
        self.logger = logging.getLogger(__name__)

    def __str__(self):
        """Return string representation used in banner on startup."""
        return type(self).__name__

    async def __aenter__(self):
        """Async context manager enter."""
        await self.start()

    async def __aexit__(self, err_type, err_value, err_t):
        """Async context manager exit."""
        if err_type and err_type != asyncio.CancelledError:
            self.logger.exception("Exception in outbound queue")
        await self.stop()

    @abstractmethod
    async def start(self):
        """Start the queue."""

    @abstractmethod
    async def stop(self):
        """Stop the queue."""

    @abstractmethod
    async def push(self, key: bytes, message: bytes):
        """Push a ``message`` to queue on ``key``."""

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
