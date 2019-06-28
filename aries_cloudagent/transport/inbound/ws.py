"""Websockets Transport classes and functions."""

import logging
from typing import Coroutine

from aiohttp import web, WSMsgType

from ...messaging.socket import SocketRef

from .base import BaseInboundTransport, InboundTransportSetupError


class WsTransport(BaseInboundTransport):
    """Websockets Transport class."""

    def __init__(
        self,
        host: str,
        port: int,
        message_router: Coroutine,
        register_socket: Coroutine,
    ) -> None:
        """
        Initialize a Transport instance.

        Args:
            host: Host to listen on
            port: Port to listen on
            message_router: Function to pass incoming messages to
            register_socket: A coroutine for registering a new socket

        """
        self.host = host
        self.port = port
        self.message_router = message_router
        self.register_socket = register_socket
        self.site = None

        # TODO: set scheme dynamically based on SSL settings (ws/wss)
        self._scheme = "ws"
        self.logger = logging.getLogger(__name__)

    @property
    def scheme(self):
        """Accessor for this transport's scheme."""
        return self._scheme

    async def make_application(self) -> web.Application:
        """Construct the aiohttp application."""
        app = web.Application()
        app.add_routes([web.get("/", self.inbound_message_handler)])
        return app

    async def start(self) -> None:
        """
        Start this transport.

        Raises:
            InboundTransportSetupError: If there was an error starting the webserver

        """
        app = await self.make_application()
        runner = web.AppRunner(app)
        await runner.setup()
        self.site = web.TCPSite(runner, host=self.host, port=self.port)
        try:
            await self.site.start()
        except OSError:
            raise InboundTransportSetupError(
                "Unable to start websocket server with host "
                + f"'{self.host}' and port '{self.port}'\n"
            )

    async def stop(self) -> None:
        """Stop this transport."""
        if self.site:
            await self.site.stop()
            self.site = None

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
            if isinstance(result, str):
                await ws.send_json(result)
            else:
                await ws.send_bytes(result)

        socket: SocketRef = await self.register_socket(handler=reply)

        # Listen for incoming messages
        async for msg in ws:
            self.logger.info(f"Received message: {msg.data}")
            if msg.type in (WSMsgType.TEXT, WSMsgType.BINARY):
                try:
                    # Route message and provide connection instance as means to respond
                    await self.message_router(msg.data, self._scheme, socket.socket_id)
                except Exception:
                    self.logger.exception("Error handling message")

            elif msg.type == WSMsgType.ERROR:
                self.logger.error(
                    f"Websocket connection closed with exception {ws.exception()}"
                )

            else:
                self.logger.warning(f"Unexpected websocket message type {msg.type}")

        self.logger.info("Websocket connection closed")

        await socket.close()

        return ws
