"""Websockets outbound transport."""

import logging

from aiohttp import ClientSession

from ...messaging.outbound_message import OutboundMessage

from .base import BaseOutboundTransport
from .queue.base import BaseOutboundMessageQueue


class WsTransport(BaseOutboundTransport):
    """Websockets outbound transport class."""

    schemes = ("ws", "wss")

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
            # As an example, we can open a websocket channel, send a message, then
            # close the channel immediately. This is not optimal but it works.
            async with self.client_session.ws_connect(message.endpoint) as ws:
                if isinstance(message.payload, bytes):
                    await ws.send_bytes(message.payload)
                else:
                    await ws.send_str(message.payload)
        except Exception:
            # TODO: add retry logic
            self.logger.exception("Error handling outbound message")
