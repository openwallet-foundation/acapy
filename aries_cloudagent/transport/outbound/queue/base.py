"""Base classes for the queue module."""
from abc import ABC, abstractmethod
import asyncio
from typing import Union

from ...error import TransportError


class BaseOutboundQueue(ABC):
    """Base class for the outbound queue generic type."""

    protocol = None  # string value representing protocol, e.g. "redis"

    def __init__(self, connection: str, prefix: str = None):
        """Initialize base queue type."""
        self.connection = connection
        self.prefix = prefix or "acapy"

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
