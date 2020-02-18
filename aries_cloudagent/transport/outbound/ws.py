"""Websockets outbound transport."""

import logging
from typing import Union

from aiohttp import ClientSession, DummyCookieJar

from .base import BaseOutboundTransport


class WsTransport(BaseOutboundTransport):
    """Websockets outbound transport class."""

    schemes = ("ws", "wss")

    def __init__(self) -> None:
        """Initialize an `WsTransport` instance."""
        super(WsTransport, self).__init__()
        self.logger = logging.getLogger(__name__)

    async def start(self):
        """Start the outbound transport."""
        self.client_session = ClientSession(cookie_jar=DummyCookieJar())
        return self

    async def stop(self):
        """Stop the outbound transport."""
        await self.client_session.close()
        self.client_session = None

    async def handle_message(self, payload: Union[str, bytes], endpoint: str):
        """
        Handle message from queue.

        Args:
            message: `OutboundMessage` to send over transport implementation
        """
        # aiohttp should automatically handle websocket sessions
        async with self.client_session.ws_connect(endpoint) as ws:
            if isinstance(payload, bytes):
                await ws.send_bytes(payload)
            else:
                await ws.send_str(payload)
