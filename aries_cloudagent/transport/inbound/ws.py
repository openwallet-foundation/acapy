"""Websockets Transport classes and functions."""

import logging

from aiohttp import web, WSMsgType

from ...messaging.error import MessageParseError

from .base import BaseInboundTransport, InboundTransportSetupError

LOGGER = logging.getLogger(__name__)


class WsTransport(BaseInboundTransport):
    """Websockets Transport class."""

    def __init__(self, host: str, port: int, create_session) -> None:
        """
        Initialize a Transport instance.

        Args:
            host: Host to listen on
            port: Port to listen on
            create_session: Method to create a new inbound session

        """
        super().__init__("ws", create_session)
        self.host = host
        self.port = port
        self.site: web.BaseSite = None

        # TODO: set scheme dynamically based on SSL settings (ws/wss)

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

        client_info = {"host": request.host, "remote": request.remote}

        session = await self.create_session(client_info)

        async with session:
            # Listen for incoming messages
            async for msg in ws:
                LOGGER.info(f"Received message: {msg.data}")
                if msg.type in (WSMsgType.TEXT, WSMsgType.BINARY):
                    try:
                        await session.receive(msg.data)
                    except MessageParseError:
                        raise web.HTTPBadRequest()

                elif msg.type == WSMsgType.ERROR:
                    LOGGER.error(
                        f"Websocket connection closed with exception {ws.exception()}"
                    )

                else:
                    LOGGER.warning(f"Unexpected websocket message type {msg.type}")

            LOGGER.info("Websocket connection closed")

        return ws
