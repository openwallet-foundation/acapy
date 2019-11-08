import asyncio

from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop, unused_port
from aiohttp import web
from asynctest import TestCase as AsyncTestCase
from asynctest.mock import patch

from ...config.default_context import DefaultContextBuilder
from ...config.injection_context import InjectionContext
from ...config.provider import ClassProvider
from ...messaging.outbound_message import OutboundMessage
from ...messaging.protocol_registry import ProtocolRegistry
from ...transport.outbound.queue.base import BaseOutboundMessageQueue
from ...transport.outbound.queue.basic import BasicOutboundMessageQueue

from ..server import AdminServer


class TestAdminServerBasic(AsyncTestCase):
    async def setUp(self):
        self.message_results = []

    def get_admin_server(
        self, settings: dict = None, context: InjectionContext = None
    ) -> AdminServer:
        if not context:
            context = InjectionContext()
        context.injector.bind_provider(
            BaseOutboundMessageQueue, ClassProvider(BasicOutboundMessageQueue)
        )
        if settings:
            context.update_settings(settings)
        return AdminServer(
            "0.0.0.0", unused_port(), context, self.outbound_message_router
        )

    async def outbound_message_router(self, *args):
        self.message_results.append(args)

    async def test_start_stop(self):
        with self.assertRaises(AssertionError):
            await self.get_admin_server().start()

        settings = {"admin.admin_insecure_mode": False}
        with self.assertRaises(AssertionError):
            await self.get_admin_server(settings).start()

        settings = {
            "admin.admin_insecure_mode": True,
            "admin.admin_api_key": "test-api-key",
        }
        with self.assertRaises(AssertionError):
            await self.get_admin_server(settings).start()

        settings = {
            "admin.admin_insecure_mode": False,
            "admin.admin_api_key": "test-api-key",
        }
        server = self.get_admin_server(settings)
        await server.start()
        await server.stop()

    async def test_responder_send(self):
        message = OutboundMessage("{}")
        admin_server = self.get_admin_server()
        await admin_server.responder.send_outbound(message)
        assert self.message_results == [(message,)]

    @unittest_run_loop
    async def test_responder_webhook(self):
        with patch.object(AdminServer, "send_webhook", autospec=True) as sender:
            admin_server = self.get_admin_server()
            test_topic = "test_topic"
            test_payload = {"test": "TEST"}
            await admin_server.responder.send_webhook(test_topic, test_payload)
            sender.assert_awaited_once_with(admin_server, test_topic, test_payload)

    async def test_import_routes(self):
        # this test just imports all default admin routes
        # for routes with associated tests, this shouldn't make a difference in coverage
        context = InjectionContext()
        context.injector.bind_instance(ProtocolRegistry, ProtocolRegistry())
        await DefaultContextBuilder().load_plugins(context)
        server = self.get_admin_server({"admin.admin_insecure_mode": True}, context)
        app = await server.make_application()


class TestAdminServerClient(AioHTTPTestCase):
    async def setUpAsync(self):
        self.message_results = []

    async def get_application(self):
        """
        Override the get_app method to return your application.
        """
        return await self.get_admin_server().make_application()

    async def outbound_message_router(self, *args):
        self.message_results.append(args)

    def get_admin_server(self) -> AdminServer:
        context = InjectionContext()
        context.injector.bind_provider(
            BaseOutboundMessageQueue, ClassProvider(BasicOutboundMessageQueue)
        )
        context.settings["admin.admin_insecure_mode"] = True
        server = AdminServer(
            "0.0.0.0", unused_port(), context, self.outbound_message_router
        )
        return server

    # the unittest_run_loop decorator can be used in tandem with
    # the AioHTTPTestCase to simplify running
    # tests that are asynchronous
    @unittest_run_loop
    async def test_index(self):
        resp = await self.client.request("GET", "/", allow_redirects=False)
        assert resp.status == 302

    @unittest_run_loop
    async def test_swagger(self):
        resp = await self.client.request("GET", "/api/doc")
        assert resp.status == 200
        text = await resp.text()
        assert "Swagger UI" in text

    @unittest_run_loop
    async def test_status(self):
        resp = await self.client.request("GET", "/status")
        result = await resp.json()
        assert isinstance(result, dict)
        resp = await self.client.request("POST", "/status/reset")
        assert resp.status == 200

    @unittest_run_loop
    async def test_websocket(self):
        async with self.client.ws_connect("/ws") as ws:
            result = await ws.receive_json()
            assert result["topic"] == "settings"


class TestAdminServerSecure(AioHTTPTestCase):
    TEST_API_KEY = "test-api-key"

    async def get_application(self):
        """
        Override the get_app method to return your application.
        """
        return await self.get_admin_server().make_application()

    async def outbound_message_router(self, *args):
        self.message_results.append(args)

    def get_admin_server(self) -> AdminServer:
        context = InjectionContext()
        context.injector.bind_provider(
            BaseOutboundMessageQueue, ClassProvider(BasicOutboundMessageQueue)
        )
        context.settings["admin.admin_api_key"] = self.TEST_API_KEY
        self.server = AdminServer(
            "0.0.0.0", unused_port(), context, self.outbound_message_router
        )
        return self.server

    @unittest_run_loop
    async def test_status_insecure(self):
        resp = await self.client.request("GET", "/status")
        assert resp.status == 401

    @unittest_run_loop
    async def test_status_secure(self):
        resp = await self.client.request(
            "GET", "/status", headers={"x-api-key": self.TEST_API_KEY}
        )
        result = await resp.json()
        assert isinstance(result, dict)


class TestAdminServerWebhook(AioHTTPTestCase):
    async def setUpAsync(self):
        self.hook_results = []

    async def receive_hook(self, request):
        topic = request.match_info["topic"]
        payload = await request.json()
        self.hook_results.append((topic, payload))
        raise web.HTTPOk()

    async def outbound_message_router(self, *args):
        pass

    def get_admin_server(self) -> AdminServer:
        context = InjectionContext()
        context.injector.bind_provider(
            BaseOutboundMessageQueue, ClassProvider(BasicOutboundMessageQueue)
        )
        context.settings["admin.admin_insecure_mode"] = True
        server = AdminServer(
            "0.0.0.0", unused_port(), context, self.outbound_message_router
        )
        return server

    async def get_application(self):
        """
        Override the get_app method to return your application.
        """
        app = web.Application()
        app.add_routes([web.post("/topic/{topic}/", self.receive_hook)])
        return app

    @unittest_run_loop
    async def test_webhook(self):
        server_addr = f"http://localhost:{self.server.port}"
        admin_server = self.get_admin_server()
        await admin_server.start()

        admin_server.add_webhook_target(server_addr)
        test_topic = "test_topic"
        test_payload = {"test": "TEST"}
        await admin_server.send_webhook(test_topic, test_payload)
        await asyncio.wait_for(admin_server.complete_webhooks(), 5.0)
        assert self.hook_results == [(test_topic, test_payload)]

        admin_server.remove_webhook_target(server_addr)
        assert admin_server.webhook_targets == {}

        await admin_server.stop()
