"""
This can be used to connect and send messages as a websocket _client_ only
"""

import asyncio
import json
import logging
import socket
from typing import Callable

from aiohttp import web, ClientSession, WSMsgType

from .message import OutboundMessage
from .base import BaseOutboundTransport
from .queue.base import BaseOutboundMessageQueue


class WsTransport(BaseOutboundTransport):
    schemes = ("ws", "wss")

    def __init__(self, queue: BaseOutboundMessageQueue) -> None:
        self.logger = logging.getLogger(__name__)
        self._queue = queue

    async def __aenter__(self):
        self.client_session = ClientSession()
        return self

    async def __aexit__(self, *err):
        await self.client_session.close()
        self.client_session = None
        self.logger.error(err)

    @property
    def queue(self):
        return self._queue

    async def handle_message(self, message: OutboundMessage):
        try:
            # As an example, we can open a websocket channel, send a message, then
            # close the channel immediately. This is not optimal but it works.
            async with self.client_session.ws_connect(message.uri) as ws:
                await ws.send_json(message.data)
        except Exception as e:
            # TODO: add retry logic
            self.logger.error(f"Error handling outbound message: {str(e)}")
