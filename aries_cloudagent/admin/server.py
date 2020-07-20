"""Admin server classes."""

import asyncio
import json
import logging
from typing import Callable, Coroutine, Sequence, Set
import uuid

from aiohttp import web
from aiohttp_apispec import (
    docs,
    response_schema,
    setup_aiohttp_apispec,
    validation_middleware,
)
import aiohttp_cors

from marshmallow import fields, Schema

from ..config.injection_context import InjectionContext
from ..core.plugin_registry import PluginRegistry
from ..messaging.responder import BaseResponder
from ..transport.queue.basic import BasicMessageQueue
from ..transport.outbound.message import OutboundMessage
from ..utils.stats import Collector
from ..utils.task_queue import TaskQueue
from ..version import __version__

from .base_server import BaseAdminServer
from .error import AdminSetupError


LOGGER = logging.getLogger(__name__)


@web.middleware
async def forensic_middleware(request: web.BaseRequest, handler: Coroutine):
    """Show input."""

    print(f'\n==== REQUEST {request.url}')
    print(f'Method: {request.method}')
    print(f'Match-info: {json.dumps(request.match_info, indent=4)}')
    print(f'Query: {json.dumps([q for q in request.query])}')
    try:
        body = await request.json()
        print(f'Body: {json.dumps(body, indent=4)}')
    except json.decoder.JSONDecodeError:
        print(f'Body: no body')

    return await handler(request)


class AdminModulesSchema(Schema):
    """Schema for the modules endpoint."""

    result = fields.List(
        fields.Str(description="admin module"), description="List of admin modules"
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
        self,
        endpoint: str,
        topic_filter: Sequence[str] = None,
        max_attempts: int = None,
    ):
        """Initialize the webhook target."""
        self.endpoint = endpoint
        self.max_attempts = max_attempts
        self._topic_filter = None
        self.topic_filter = topic_filter  # call setter

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
        self.admin_api_key = context.settings.get("admin.admin_api_key")
        self.admin_insecure_mode = bool(
            context.settings.get("admin.admin_insecure_mode")
        )
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

        middlewares = [forensic_middleware, validation_middleware]

        # admin-token and admin-token are mutually exclusive and required.
        # This should be enforced during parameter parsing but to be sure,
        # we check here.
        assert self.admin_insecure_mode ^ bool(self.admin_api_key)

        def is_unprotected_path(path: str):
            return path in [
                "/api/doc",
                "/api/docs/swagger.json",
                "/favicon.ico",
                "/ws",  # ws handler checks authentication
            ] or path.startswith("/static/swagger/")

        # If admin_api_key is None, then admin_insecure_mode must be set so
        # we can safely enable the admin server with no security
        if self.admin_api_key:

            @web.middleware
            async def check_token(request, handler):
                header_admin_api_key = request.headers.get("x-api-key")
                valid_key = self.admin_api_key == header_admin_api_key

                if valid_key or is_unprotected_path(request.path):
                    return await handler(request)
                else:
                    raise web.HTTPUnauthorized()

            middlewares.append(check_token)

        collector: Collector = await self.context.inject(Collector, required=False)

        if self.task_queue:

            @web.middleware
            async def apply_limiter(request, handler):
                task = await self.task_queue.put(handler(request))
                return await task

            middlewares.append(apply_limiter)

        elif collector:

            @web.middleware
            async def collect_stats(request, handler):
                handler = collector.wrap_coro(handler, [handler.__qualname__])
                return await handler(request)

            middlewares.append(collect_stats)

        app = web.Application(middlewares=middlewares)
        app["request_context"] = self.context
        app["outbound_message_router"] = self.responder.send

        app.add_routes(
            [
                web.get("/", self.redirect_handler, allow_head=False),
                web.get("/plugins", self.plugins_handler, allow_head=False),
                web.get("/status", self.status_handler, allow_head=False),
                web.post("/status/reset", self.status_reset_handler),
                web.get("/ws", self.websocket_handler, allow_head=False),
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
        agent_label = self.context.settings.get("default_label")
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

        plugin_registry: PluginRegistry = await self.context.inject(
            PluginRegistry, required=False
        )
        if plugin_registry:
            plugin_registry.post_process_routes(self.app)

        # order tags alphabetically, parameters deterministically and pythonically
        swagger_dict = self.app._state["swagger_dict"]
        swagger_dict.get("tags", []).sort(key=lambda t: t["name"])
        for path in swagger_dict["paths"].values():
            for method_spec in path.values():
                method_spec["parameters"].sort(
                    key=lambda p: (p["in"], not p["required"], p["name"])
                )

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
        if self.admin_api_key:
            swagger = app["swagger_dict"]
            swagger["securityDefinitions"] = {
                "ApiKeyHeader": {"type": "apiKey", "in": "header", "name": "X-API-KEY"}
            }
            swagger["security"] = [{"ApiKeyHeader": []}]

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
        status["label"] = self.context.settings.get("default_label")
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

        if self.admin_insecure_mode:
            # open to send websocket messages without api key auth
            queue.authenticated = True
        else:
            header_admin_api_key = request.headers.get("x-api-key")
            # authenticated via http header?
            queue.authenticated = header_admin_api_key == self.admin_api_key

        try:
            self.websocket_queues[socket_id] = queue
            await queue.enqueue(
                {
                    "topic": "settings",
                    "payload": {
                        "authenticated": queue.authenticated,
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
            receive = loop.create_task(ws.receive_json())
            send = loop.create_task(queue.dequeue(timeout=5.0))

            while not closed:
                try:
                    await asyncio.wait(
                        (receive, send), return_when=asyncio.FIRST_COMPLETED
                    )
                    if ws.closed:
                        closed = True

                    if receive.done():
                        if not closed:
                            msg_received = None
                            msg_api_key = None
                            try:
                                # this call can re-raise exeptions from inside the task
                                msg_received = receive.result()
                                msg_api_key = msg_received.get("x-api-key")
                            except Exception:
                                LOGGER.exception(
                                    "Exception in websocket receiving task:"
                                )
                            if self.admin_api_key and self.admin_api_key == msg_api_key:
                                # authenticated via websocket message
                                queue.authenticated = True

                            receive = loop.create_task(ws.receive_json())

                    if send.done():
                        try:
                            msg = send.result()
                        except asyncio.TimeoutError:
                            msg = None

                        if msg is None:
                            # we send fake pings because the JS client
                            # can't detect real ones
                            msg = {
                                "topic": "ping",
                                "authenticated": queue.authenticated,
                            }
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
        self,
        target_url: str,
        topic_filter: Sequence[str] = None,
        max_attempts: int = None,
    ):
        """Add a webhook target."""
        self.webhook_targets[target_url] = WebhookTarget(
            target_url, topic_filter, max_attempts
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
                    self.webhook_router(
                        topic, payload, target.endpoint, target.max_attempts
                    )

        for queue in self.websocket_queues.values():
            if queue.authenticated or topic in ("ping", "settings"):
                await queue.enqueue({"topic": topic, "payload": payload})
