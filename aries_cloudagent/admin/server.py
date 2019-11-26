"""Admin server classes."""

import asyncio
import logging
from typing import Coroutine, Sequence, Set
import uuid

from aiohttp import web, ClientSession, DummyCookieJar
from aiohttp_apispec import docs, response_schema, setup_aiohttp_apispec
import aiohttp_cors

from marshmallow import fields, Schema

from ..config.injection_context import InjectionContext
from ..messaging.outbound_message import OutboundMessage
from ..messaging.plugin_registry import PluginRegistry
from ..messaging.responder import BaseResponder
from ..stats import Collector
from ..task_processor import TaskProcessor
from ..transport.outbound.queue.base import BaseOutboundMessageQueue
from ..transport.stats import StatsTracer

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

    def __init__(self, send: Coroutine, webhook: Coroutine, **kwargs):
        """
        Initialize an instance of `AdminResponder`.

        Args:
            send: Function to send outbound message

        """
        super().__init__(**kwargs)
        self._send = send
        self._webhook = webhook

    async def send_outbound(self, message: OutboundMessage):
        """
        Send outbound message.

        Args:
            message: The `OutboundMessage` to be sent
        """
        await self._send(message)

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
    ):
        """
        Initialize an AdminServer instance.

        Args:
            host: Host to listen on
            port: Port to listen on

        """
        self.app = None
        self.host = host
        self.port = port
        self.loaded_modules = []
        self.webhook_queue = None
        self.webhook_retries = 5
        self.webhook_session: ClientSession = None
        self.webhook_targets = {}
        self.webhook_task = None
        self.webhook_processor: TaskProcessor = None
        self.websocket_queues = {}
        self.site = None

        self.context = context.start_scope("admin")
        self.responder = AdminResponder(outbound_message_router, self.send_webhook)
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
                web.get("/modules", self.modules_handler),
                web.get("/status", self.status_handler),
                web.post("/status/reset", self.status_reset_handler),
                web.get("/ws", self.websocket_handler),
            ]
        )

        plugin_registry = await self.context.inject(PluginRegistry, required=False)
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
        if self.webhook_queue:
            self.webhook_queue.stop()
            self.webhook_queue = None
        if self.webhook_session:
            await self.webhook_session.close()
            self.webhook_session = None

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
        status = {"version": __version__}
        collector: Collector = await self.context.inject(Collector, required=False)
        if collector:
            status["timing"] = collector.results
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
        queue = await self.context.inject(BaseOutboundMessageQueue)

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
            while not closed:
                try:
                    msg = await queue.dequeue(timeout=5.0)
                    if msg is None:
                        # we send fake pings because the JS client
                        # can't detect real ones
                        msg = {"topic": "ping"}
                    if ws.closed:
                        closed = True
                    if msg and not closed:
                        await ws.send_json(msg)
                except asyncio.CancelledError:
                    closed = True

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
        if not self.webhook_queue:
            self.webhook_queue = await self.context.inject(BaseOutboundMessageQueue)
            self.webhook_task = asyncio.get_event_loop().create_task(
                self._process_webhooks()
            )
        await self.webhook_queue.enqueue((topic, payload))

    async def _process_webhooks(self):
        """Continuously poll webhook queue and dispatch to targets."""
        session_args = {}
        collector: Collector = await self.context.inject(Collector, required=False)
        if collector:
            session_args["trace_configs"] = [StatsTracer(collector, "webhook-http:")]
        session_args["cookie_jar"] = DummyCookieJar()
        self.webhook_session = ClientSession(**session_args)
        self.webhook_processor = TaskProcessor(max_pending=20)
        async for topic, payload in self.webhook_queue:
            for queue in self.websocket_queues.values():
                await queue.enqueue({"topic": topic, "payload": payload})
            if self.webhook_targets:
                targets = self.webhook_targets.copy()
                for idx, target in targets.items():
                    if not target.topic_filter or topic in target.topic_filter:
                        retries = (
                            self.webhook_retries
                            if target.retries is None
                            else target.retries
                        )
                        await self.webhook_processor.run_retry(
                            lambda pending: self._perform_send_webhook(
                                target.endpoint, topic, payload, pending.attempts + 1
                            ),
                            ident=(target.endpoint, topic),
                            retries=retries,
                        )
            self.webhook_queue.task_done()

    async def _perform_send_webhook(
        self, target_url: str, topic: str, payload: dict, attempt: int = None
    ):
        """Dispatch a webhook to a specific endpoint."""
        full_webhook_url = f"{target_url}/topic/{topic}/"
        attempt_str = f" (attempt {attempt})" if attempt else ""
        LOGGER.debug("Sending webhook to : %s%s", full_webhook_url, attempt_str)
        async with self.webhook_session.post(
            full_webhook_url, json=payload
        ) as response:
            if response.status < 200 or response.status > 299:
                # raise Exception(f"Unexpected response status {response.status}")
                raise Exception(
                    f"Unexpected: target {target_url}\n"
                    f"full {full_webhook_url}\n"
                    f"response {response}"
                )

    async def complete_webhooks(self):
        """Wait for all pending webhooks to be dispatched, used in testing."""
        if self.webhook_queue:
            await self.webhook_queue.join()
            self.webhook_queue.reset()
        if self.webhook_processor:
            await self.webhook_processor.wait_done()
