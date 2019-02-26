"""Websockets Transport classes and functions."""

import logging
from typing import Callable

from aiohttp import web, WSMsgType

from .base import BaseInboundTransport
from ...error import BaseError


class WsSetupError(BaseError):
    """Websocket setup error."""

    pass


class Transport(BaseInboundTransport):
    """Websockets Transport class."""

    def __init__(self, host: str, port: int, message_router: Callable) -> None:
        """
        Initialize a Transport instance.

        Args:
            host: Host to listen on
            port: Port to listen on
            message_router: Function to pass incoming messages to

        """
        self.host = host
        self.port = port
        self.message_router = message_router

        # TODO: set scheme dynamically based on SSL settings (ws/wss)
        self._scheme = "ws"
        self.logger = logging.getLogger(__name__)

    @property
    def scheme(self):
        """Accessor for this transport's scheme."""
        return self._scheme

    async def start(self) -> None:
        """
        Start this transport.

        Raises:
            HttpSetupError: If there was an error starting the webserver

        """
        app = web.Application()
        app.add_routes([web.get("/", self.inbound_message_handler)])
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host=self.host, port=self.port)
        try:
            await site.start()
        except OSError:
            raise WsSetupError(
                "Unable to start webserver with host "
                + f"'{self.host}' and port '{self.port}'\n"
            )

    async def inbound_message_handler(self, request):
        """
        Message handler for inbound messages.

        Args:
            request: aiohttp request object

        Returns:
            The web response

        """
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        async def reply(result):
            await ws.send_json({"success": True, "message": result})

        # Listen for incoming messages
        async for msg in ws:
            self.logger.info(f"Received message: {msg.data}")
            if msg.type == WSMsgType.TEXT and msg.data == "close":
                await ws.close()

            elif msg.type in (WSMsgType.TEXT, WSMsgType.BINARY):
                try:
                    # Route message and provide connection instance as means to respond
                    result = await self.message_router(msg.data, self._scheme, reply)
                    if result:
                        await reply(result)
                except Exception as e:
                    self.logger.exception("Error handling message")
                    error_message = f"Error handling message: {str(e)}"
                    await ws.send_json({"success": False, "message": error_message})
                    continue

            elif msg.type == WSMsgType.ERROR:
                self.logger.error(
                    f"Websocket connection closed with exception {ws.exception()}"
                )

        self.logger.info("Websocket connection closed")
        return ws
