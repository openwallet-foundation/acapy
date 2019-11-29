"""Admin server classes."""

import asyncio
import logging
from typing import Callable, Coroutine, Sequence, Set
import uuid

from aiohttp import web
from aiohttp_apispec import docs, response_schema, setup_aiohttp_apispec
import aiohttp_cors

from marshmallow import fields, Schema

from ..config.injection_context import InjectionContext
from ..messaging.plugin_registry import PluginRegistry
from ..messaging.responder import BaseResponder
from ..messaging.task_queue import TaskQueue
from ..stats import Collector
from ..transport.queue.basic import BasicMessageQueue
from ..transport.outbound.message import OutboundMessage

from .base_server import BaseAdminServer
from .error import AdminSetupError

from ..version import __version__

LOGGER = logging.getLogger(__name__)


class AdminModulesSchema(Schema):
    """Schema for the modules endpoint."""

    result = fields.List(
        fields.Str(description="admin module"), description="List of admin modules",
    )


class AdminStatusSchema(Schema):
    """Schema for the status endpoint."""


class AdminResponder(BaseResponder):
    """Handle outgoing messages from message handlers."""

    def __init__(
        self, context: InjectionContext, send: Coroutine, webhook: Coroutine, **kwargs
    ):
        """
        Initialize an instance of `AdminResponder`.

        Args:
            send: Function to send outbound message

        """
        super().__init__(**kwargs)
        self._context = context
        self._send = send
        self._webhook = webhook

    async def send_outbound(self, message: OutboundMessage):
        """
        Send outbound message.

        Args:
            message: The `OutboundMessage` to be sent
        """
        await self._send(self._context, message)

    async def send_webhook(self, topic: str, payload: dict):
        """
        Dispatch a webhook.

        Args:
            topic: the webhook topic identifier
            payload: the webhook payload value
        """
        await self._webhook(topic, payload)


class WebhookTarget:
    """Class for managing webhook target information."""

    def __init__(
        self, endpoint: str, topic_filter: Sequence[str] = None, retries: int = None
    ):
        """Initialize the webhook target."""
        self.endpoint = endpoint
        self._topic_filter = None
        self.retries = retries
        # call setter
        self.topic_filter = topic_filter

    @property
    def topic_filter(self) -> Set[str]:
        """Accessor for the target's topic filter."""
        return self._topic_filter

    @topic_filter.setter
    def topic_filter(self, val: Sequence[str]):
        """Setter for the target's topic filter."""
        filter = set(val) if val else None
        if filter and "*" in filter:
            filter = None
        self._topic_filter = filter


class AdminServer(BaseAdminServer):
    """Admin HTTP server class."""

    def __init__(
        self,
        host: str,
        port: int,
        context: InjectionContext,
        outbound_message_router: Coroutine,
        webhook_router: Callable,
        task_queue: TaskQueue = None,
        conductor_stats: Coroutine = None,
    ):
        """
        Initialize an AdminServer instance.

        Args:
            host: Host to listen on
            port: Port to listen on
            context: The application context instance
            outbound_message_router: Coroutine for delivering outbound messages
            webhook_router: Callable for delivering webhooks
            task_queue: An optional task queue for handlers
        """
        self.app = None
        self.host = host
        self.port = port
        self.conductor_stats = conductor_stats
        self.loaded_modules = []
        self.task_queue = task_queue
        self.webhook_router = webhook_router
        self.webhook_targets = {}
        self.websocket_queues = {}
        self.site = None

        self.context = context.start_scope("admin")
        self.responder = AdminResponder(
            self.context, outbound_message_router, self.send_webhook
        )
        self.context.injector.bind_instance(BaseResponder, self.responder)

    async def make_application(self) -> web.Application:
        """Get the aiohttp application instance."""

        middlewares = []

        admin_api_key = self.context.settings.get("admin.admin_api_key")
        admin_insecure_mode = self.context.settings.get("admin.admin_insecure_mode")

        # admin-token and admin-token are mutually exclusive and required.
        # This should be enforced during parameter parsing but to be sure,
        # we check here.
        assert admin_insecure_mode or admin_api_key
        assert not (admin_insecure_mode and admin_api_key)

        # If admin_api_key is None, then admin_insecure_mode must be set so
        # we can safely enable the admin server with no security
        if admin_api_key:

            @web.middleware
            async def check_token(request, handler):
                header_admin_api_key = request.headers.get("x-api-key")
                if not header_admin_api_key:
                    raise web.HTTPUnauthorized()

                if admin_api_key == header_admin_api_key:
                    return await handler(request)
                else:
                    raise web.HTTPUnauthorized()

            middlewares.append(check_token)

        if self.task_queue:

            @web.middleware
            async def apply_limiter(request, handler):
                task = await self.task_queue.put(handler(request))
                return await task

            middlewares.append(apply_limiter)

        stats: Collector = await self.context.inject(Collector, required=False)
        if stats:

            @web.middleware
            async def collect_stats(request, handler):
                handler = stats.wrap_coro(
                    handler, [handler.__qualname__, "any-admin-request"]
                )
                return await handler(request)

            middlewares.append(collect_stats)

        app = web.Application(middlewares=middlewares)
        app["request_context"] = self.context
        app["outbound_message_router"] = self.responder.send

        app.add_routes(
            [
                web.get("/", self.redirect_handler),
                web.get("/plugins", self.plugins_handler),
                web.get("/status", self.status_handler),
                web.post("/status/reset", self.status_reset_handler),
                web.get("/ws", self.websocket_handler),
            ]
        )

        plugin_registry: PluginRegistry = await self.context.inject(
            PluginRegistry, required=False
        )
        if plugin_registry:
            await plugin_registry.register_admin_routes(app)

        cors = aiohttp_cors.setup(
            app,
            defaults={
                "*": aiohttp_cors.ResourceOptions(
                    allow_credentials=True,
                    expose_headers="*",
                    allow_headers="*",
                    allow_methods="*",
                )
            },
        )
        for route in app.router.routes():
            cors.add(route)
        # get agent label
        agent_label = self.context.settings.get("default_label"),
        version_string = f"v{__version__}"

        setup_aiohttp_apispec(
            app=app, title=agent_label, version=version_string, swagger_path="/api/doc"
        )
        app.on_startup.append(self.on_startup)
        return app

    async def start(self) -> None:
        """
        Start the webserver.

        Raises:
            AdminSetupError: If there was an error starting the webserver

        """
        self.app = await self.make_application()
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
        for queue in self.websocket_queues.values():
            queue.stop()
        if self.site:
            await self.site.stop()
            self.site = None

    async def on_startup(self, app: web.Application):
        """Perform webserver startup actions."""

    @docs(tags=["server"], summary="Fetch the list of loaded plugins")
    @response_schema(AdminModulesSchema(), 200)
    async def plugins_handler(self, request: web.BaseRequest):
        """
        Request handler for the loaded plugins list.

        Args:
            request: aiohttp request object

        Returns:
            The module list response

        """
        registry: PluginRegistry = await self.context.inject(
            PluginRegistry, required=False
        )
        print(registry)
        plugins = registry and sorted(registry.plugin_names) or []
        return web.json_response({"result": plugins})

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
        status = {"version": __version__}
        collector: Collector = await self.context.inject(Collector, required=False)
        if collector:
            status["timing"] = collector.results
        if self.conductor_stats:
            status["conductor"] = await self.conductor_stats()
        return web.json_response(status)

    @docs(tags=["server"], summary="Reset statistics")
    @response_schema(AdminStatusSchema(), 200)
    async def status_reset_handler(self, request: web.BaseRequest):
        """
        Request handler for resetting the timing statistics.

        Args:
            request: aiohttp request object

        Returns:
            The web response

        """
        collector: Collector = await self.context.inject(Collector, required=False)
        if collector:
            collector.reset()
        return web.json_response({})

    async def redirect_handler(self, request: web.BaseRequest):
        """Perform redirect to documentation."""
        raise web.HTTPFound("/api/doc")

    async def websocket_handler(self, request):
        """Send notifications to admin client over websocket."""

        ws = web.WebSocketResponse()
        await ws.prepare(request)
        socket_id = str(uuid.uuid4())
        queue = BasicMessageQueue()
        loop = asyncio.get_event_loop()

        try:
            self.websocket_queues[socket_id] = queue
            await queue.enqueue(
                {
                    "topic": "settings",
                    "payload": {
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
            receive = loop.create_task(ws.receive())
            send = loop.create_task(queue.dequeue(timeout=5.0))

            while not closed:
                try:
                    await asyncio.wait(
                        (receive, send), return_when=asyncio.FIRST_COMPLETED
                    )
                    if ws.closed:
                        closed = True

                    if receive.done():
                        # ignored
                        if not closed:
                            receive = loop.create_task(ws.receive())

                    if send.done():
                        msg = send.result()
                        if msg is None:
                            # we send fake pings because the JS client
                            # can't detect real ones
                            msg = {"topic": "ping"}
                        if not closed:
                            if msg:
                                await ws.send_json(msg)
                            send = loop.create_task(queue.dequeue(timeout=5.0))
                except asyncio.CancelledError:
                    closed = True

            if not receive.done():
                receive.cancel()
            if not send.done():
                send.cancel()

        finally:
            del self.websocket_queues[socket_id]

        return ws

    def add_webhook_target(
        self, target_url: str, topic_filter: Sequence[str] = None, retries: int = None
    ):
        """Add a webhook target."""
        self.webhook_targets[target_url] = WebhookTarget(
            target_url, topic_filter, retries
        )

    def remove_webhook_target(self, target_url: str):
        """Remove a webhook target."""
        if target_url in self.webhook_targets:
            del self.webhook_targets[target_url]

    async def send_webhook(self, topic: str, payload: dict):
        """Add a webhook to the queue, to send to all registered targets."""
        if self.webhook_router:
            for idx, target in self.webhook_targets.items():
                if not target.topic_filter or topic in target.topic_filter:
                    self.webhook_router(topic, payload, target.endpoint, target.retries)

        for queue in self.websocket_queues.values():
            await queue.enqueue({"topic": topic, "payload": payload})
