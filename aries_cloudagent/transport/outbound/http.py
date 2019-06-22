"""Http outbound transport."""

import asyncio
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
        super(HttpTransport, self).__init__(queue)
        self.logger = logging.getLogger(__name__)

    async def __aenter__(self):
        """Async context manager enter."""
        self.client_session = ClientSession()
        return self

    async def __aexit__(self, err_type, err_value, err_tb):
        """Async context manager exit."""
        await self.client_session.close()
        self.client_session = None
        if err_type and err_type != asyncio.CancelledError:
            self.logger.exception("Exception in outbound HTTP transport")

    async def handle_message(self, message: OutboundMessage):
        """
        Handle message from queue.

        Args:
            message: `OutboundMessage` to send over transport implementation
        """
        headers = {}
        if isinstance(message.payload, bytes):
            headers["Content-Type"] = "application/ssi-agent-wire"
        else:
            headers["Content-Type"] = "application/json"
        async with self.client_session.post(
            message.endpoint, data=message.payload, headers=headers
        ) as response:
            self.logger.info(response.status)
