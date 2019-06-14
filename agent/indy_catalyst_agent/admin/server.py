"""Admin server classes."""

import asyncio
from concurrent.futures import CancelledError
import logging
from typing import Coroutine
import uuid

from aiohttp import web
from aiohttp_apispec import docs, response_schema, setup_aiohttp_apispec
import aiohttp_cors

from marshmallow import fields, Schema

from ..config.injection_context import InjectionContext
from ..messaging.outbound_message import OutboundMessage
from ..messaging.responder import BaseResponder
from ..stats import Collector

from .base_server import BaseAdminServer
from .error import AdminSetupError
from .routes import register_module_routes


class AdminModulesSchema(Schema):
    """Schema for the modules endpoint."""

    result = fields.List(fields.Str())


class AdminStatusSchema(Schema):
    """Schema for the status endpoint."""


class AdminResponder(BaseResponder):
    """Handle outgoing messages from message handlers."""

    def __init__(self, send: Coroutine, **kwargs):
        """
        Initialize an instance of `AdminResponder`.

        Args:
            send: Function to send outbound message

        """
        super().__init__(**kwargs)
        self._send = send

    async def send_outbound(self, message: OutboundMessage):
        """
        Send outbound message.

        Args:
            message: The `OutboundMessage` to be sent
        """
        await self._send(message)


class AdminServer(BaseAdminServer):
    """Admin HTTP server class."""

    def __init__(
        self,
        host: str,
        port: int,
        context: InjectionContext,
        outbound_message_router: Coroutine,
    ):
        """
        Initialize an AdminServer instance.

        Args:
            host: Host to listen on
            port: Port to listen on

        """
        self.app = None
        self.context = context
        self.host = host
        self.port = port
        self.logger = logging.getLogger(__name__)
        self.loaded_modules = []
        self.notify_queues = {}
        self.responder = AdminResponder(outbound_message_router)
        self.site = None

    async def start(self) -> None:
        """
        Start the webserver.

        Raises:
            AdminSetupError: If there was an error starting the webserver

        """
        self.app = web.Application(debug=True)
        self.app["request_context"] = self.context
        self.app["outbound_message_router"] = self.responder.send

        self.app.add_routes(
            [
                web.get("/", self.redirect_handler),
                web.get("/modules", self.modules_handler),
                web.get("/status", self.status_handler),
                web.get("/ws", self.websocket_handler),
            ]
        )
        await register_module_routes(self.app)

        cors = aiohttp_cors.setup(
            self.app,
            defaults={
                "*": aiohttp_cors.ResourceOptions(
                    allow_credentials=True,
                    expose_headers="*",
                    allow_headers="*",
                    allow_methods="*",
                )
            },
        )
        for route in self.app.router.routes():
            cors.add(route)

        setup_aiohttp_apispec(
            app=self.app,
            title="Indy Catalyst Agent",
            version="v1",
            swagger_path="/api/doc",
        )
        self.app.on_startup.append(self.on_startup)

        runner = web.AppRunner(self.app)
        await runner.setup()
        self.site = web.TCPSite(runner, host=self.host, port=self.port)

        try:
            await self.site.start()
        except OSError:
            raise AdminSetupError(
                "Unable to start webserver with host "
                + f"'{self.host}' and port '{self.port}'\n"
            )

    async def stop(self) -> None:
        """Stop the webserver."""
        await self.site.stop()

    async def on_startup(self, app: web.Application):
        """Perform webserver startup actions."""

    @docs(tags=["server"], summary="Fetch the list of loaded modules")
    @response_schema(AdminModulesSchema(), 200)
    async def modules_handler(self, request: web.BaseRequest):
        """
        Request handler for the loaded modules list.

        Args:
            request: aiohttp request object

        Returns:
            The module list response

        """
        return web.json_response({"result": self.loaded_modules})

    @docs(tags=["server"], summary="Fetch the server status")
    @response_schema(AdminStatusSchema(), 200)
    async def status_handler(self, request: web.BaseRequest):
        """
        Request handler for the server status information.

        Args:
            request: aiohttp request object

        Returns:
            The web response

        """
        status = {}
        collector: Collector = await self.context.inject(Collector, required=False)
        if collector:
            status["timing"] = collector.results
        return web.json_response(status)

    async def redirect_handler(self, request: web.BaseRequest):
        """Perform redirect to documentation."""
        return web.HTTPFound("/api/doc")

    async def websocket_handler(self, request):
        """Send notifications to admin client over websocket."""

        ws = web.WebSocketResponse()
        await ws.prepare(request)
        socket_id = str(uuid.uuid4())
        queue = asyncio.Queue()
        self.notify_queues[socket_id] = queue
        await queue.put(
            {
                "type": "settings",
                "context": {
                    "label": self.context.settings.get("default_label"),
                    "endpoint": self.context.settings.get("default_endpoint"),
                    "no_receive_invites": self.context.settings.get(
                        "admin.no_receive_invites", False
                    ),
                    "help_link": self.context.settings.get("admin.help_link"),
                },
            }
        )

        closed = False
        while not closed:
            try:
                msg = await asyncio.wait_for(queue.get(), 5.0)
            except asyncio.TimeoutError:
                # we send fake pings because the JS client
                # can't detect real ones
                msg = {"type": "ping"}
            except CancelledError:
                closed = True
            if ws.closed:
                closed = True
            if msg and not closed:
                await ws.send_json(msg)

        del self.notify_queues[socket_id]

        return ws

    async def add_event(self, message: dict):
        """Add an event to existing queues."""

        for queue in self.notify_queues.values():
            await queue.put(message)
