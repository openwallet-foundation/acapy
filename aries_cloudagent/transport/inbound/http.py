"""Http Transport classes and functions."""

import logging

from aiohttp import web

from ...messaging.error import MessageParseError

from .base import BaseInboundTransport, InboundTransportSetupError

LOGGER = logging.getLogger(__name__)


class HttpTransport(BaseInboundTransport):
    """Http Transport class."""

    def __init__(self, host: str, port: int, create_session) -> None:
        """
        Initialize a Transport instance.

        Args:
            host: Host to listen on
            port: Port to listen on
            create_session: Method to create a new inbound session

        """
        super().__init__("http", create_session)
        self.host = host
        self.port = port
        self.site: web.BaseSite = None

    async def make_application(self) -> web.Application:
        """Construct the aiohttp application."""
        app = web.Application()
        app.add_routes([web.get("/", self.invite_message_handler)])
        app.add_routes([web.post("/", self.inbound_message_handler)])
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
                "Unable to start webserver with host "
                + f"'{self.host}' and port '{self.port}'\n"
            )

    async def stop(self) -> None:
        """Stop this transport."""
        if self.site:
            await self.site.stop()
            self.site = None

    async def inbound_message_handler(self, request: web.BaseRequest):
        """
        Message handler for inbound messages.

        Args:
            request: aiohttp request object

        Returns:
            The web response

        """
        ctype = request.headers.get("content-type", "")
        if ctype.split(";", 1)[0].lower() == "application/json":
            body = await request.text()
        else:
            body = await request.read()

        client_info = {"host": request.host, "remote": request.remote}

        async with self.create_session(client_info) as session:

            try:
                inbound = await session.receive_packed(body)
            except MessageParseError:
                raise web.HTTPBadRequest()

            if inbound.receipt.direct_response_requested:
                response = await session.wait_response_packed()

                # no more responses
                session.can_respond = False
                session.clear_outbound()

                if response:
                    response_body = response.payload
                    if isinstance(response_body, bytes):
                        return web.Response(
                            body=response_body,
                            status=200,
                            headers={"Content-Type": "application/ssi-agent-wire"},
                        )
                    else:
                        return web.Response(
                            text=response_body,
                            status=200,
                            headers={"Content-Type": "application/json"},
                        )

        return web.Response(status=200)

    async def invite_message_handler(self, request: web.BaseRequest):
        """
        Message handler for invites.

        Args:
            request: aiohttp request object

        Returns:
            The web response

        """
        if request.query.get("c_i"):
            return web.Response(
                text="You have received a connection invitation. To accept the "
                "invitation, paste it into your agent application."
            )
        else:
            return web.Response(status=200)
