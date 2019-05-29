"""Http Transport classes and functions."""

import asyncio
import logging
from typing import Callable

from aiohttp import web

from .base import BaseInboundTransport
from ...error import BaseError
from ...wallet.util import b64_to_bytes


class HttpSetupError(BaseError):
    """Http setup error."""

    pass


class Transport(BaseInboundTransport):
    """Http Transport class."""

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

        self._scheme = "http"
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
        app.add_routes([web.get("/", self.invite_message_handler)])
        app.add_routes([web.post("/", self.inbound_message_handler)])
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host=self.host, port=self.port)
        try:
            await site.start()
        except OSError:
            raise HttpSetupError(
                "Unable to start webserver with host "
                + f"'{self.host}' and port '{self.port}'\n"
            )

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

        try:
            response = asyncio.Future()
            await self.message_router(
                body, self._scheme, single_response=response, allow_direct_response=True
            )
        except Exception:
            self.logger.exception("Error handling message")
            return web.Response(status=400)

        try:
            await asyncio.wait_for(response, 30)
        except asyncio.TimeoutError:
            if not response.done():
                response.cancel()
            return web.Response(status=504)
        except asyncio.CancelledError:
            return web.Response(status=200)

        message = response.result()
        if message:
            if isinstance(message, bytes):
                return web.Response(
                    body=message,
                    status=200,
                    headers={"Content-Type": "application/ssi-agent-wire"},
                )
            else:
                return web.Response(
                    text=message,
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
        invite = request.query.get("invite")
        if "invite" in request.query:
            invite = b64_to_bytes(request.query["invite"], urlsafe=True)
            await self.message_router(invite, "invitation")
            return web.Response(text="Invitation received")
        elif "router" in request.query:
            invite = b64_to_bytes(request.query["router"], urlsafe=True)
            await self.message_router(invite, "router_invitation")
            return web.Response(text="Router invitation received")
        elif request.query.get("c_i"):
            return web.Response(
                text="You have received a connection invitation. To accept the "
                "invitation, paste it into your agent application."
            )
        else:
            return web.Response(text="To send an invitation add ?invite=<base64invite>")
