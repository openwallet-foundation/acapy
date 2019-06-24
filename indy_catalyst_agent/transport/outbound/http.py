"""Http outbound transport."""

import logging

from aiohttp import ClientSession

from ...messaging.outbound_message import OutboundMessage

from .base import BaseOutboundTransport
from .queue.base import BaseOutboundMessageQueue


class HttpTransport(BaseOutboundTransport):
    """Http outbound transport class."""

    schemes = ("http", "https")

    def __init__(self, queue: BaseOutboundMessageQueue) -> None:
        """Initialize an `HttpTransport` instance."""
        self.logger = logging.getLogger(__name__)
        self._queue = queue

    async def __aenter__(self):
        """Async context manager enter."""
        self.client_session = ClientSession()
        return self

    async def __aexit__(self, *err):
        """Async context manager exit."""
        await self.client_session.close()
        self.client_session = None
        self.logger.error(err)

    @property
    def queue(self):
        """Accessor for queue."""
        return self._queue

    async def handle_message(self, message: OutboundMessage):
        """
        Handle message from queue.

        Args:
            message: `OutboundMessage` to send over transport implementation
        """
        try:
            headers = {}
            if isinstance(message.payload, bytes):
                headers["Content-Type"] = "application/ssi-agent-wire"
            else:
                headers["Content-Type"] = "application/json"
            async with self.client_session.post(
                message.endpoint, data=message.payload, headers=headers
            ) as response:
                self.logger.info(response.status)
        except Exception:
            # TODO: add retry logic
            self.logger.exception("Error handling outbound message")
