"""Websockets outbound transport."""

import asyncio
import logging

from aiohttp import ClientSession

from ...messaging.outbound_message import OutboundMessage

from .base import BaseOutboundTransport
from .queue.base import BaseOutboundMessageQueue


class WsTransport(BaseOutboundTransport):
    """Websockets outbound transport class."""

    schemes = ("ws", "wss")

    def __init__(self, queue: BaseOutboundMessageQueue) -> None:
        """Initialize an `WsTransport` instance."""
        super(WsTransport, self).__init__(queue)
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
            self.logger.exception("Exception in outbound WebSocket transport")

    async def handle_message(self, message: OutboundMessage):
        """
        Handle message from queue.

        Args:
            message: `OutboundMessage` to send over transport implementation
        """
        # As an example, we can open a websocket channel, send a message, then
        # close the channel immediately. This is not optimal but it works.
        async with self.client_session.ws_connect(message.endpoint) as ws:
            if isinstance(message.payload, bytes):
                await ws.send_bytes(message.payload)
            else:
                await ws.send_str(message.payload)
