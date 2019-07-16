import asyncio

from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop, unused_port
from aiohttp import web

from ...config.injection_context import InjectionContext
from ...config.provider import ClassProvider
from ...transport.outbound.queue.base import BaseOutboundMessageQueue
from ...transport.outbound.queue.basic import BasicOutboundMessageQueue
from ..server import AdminServer


class TestAdminServerApp(AioHTTPTestCase):
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

    @unittest_run_loop
    async def test_start_bad_settings(self):
        server = self.get_admin_server()
        server.context.settings["admin.admin_insecure_mode"] = None
        
        try:
            await server.start()
        except AssertionError:
            return True

        raise Exception

    @unittest_run_loop
    async def test_start_stop(self):
        server = self.get_admin_server()
        await server.start()
        await server.stop()

    async def get_application(self):
        """
        Override the get_app method to return your application.
        """
        return await self.get_admin_server().make_application()

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
        print(text)
        assert "Swagger UI" in text

    @unittest_run_loop
    async def test_status(self):
        resp = await self.client.request("GET", "/status")
        result = await resp.json()
        assert isinstance(result, dict)
        resp = await self.client.request("POST", "/status/reset")
        assert resp.status == 200

    @unittest_run_loop
    async def test_status(self):
        resp = await self.client.request("GET", "/status")
        result = await resp.json()
        assert isinstance(result, dict)

    @unittest_run_loop
    async def test_websocket(self):
        async with self.client.ws_connect("/ws") as ws:
            result = await ws.receive_json()
            assert result["topic"] == "settings"


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
        server = AdminServer(
            "localhost", unused_port(), context, self.outbound_message_router
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
        admin_server.add_webhook_target(server_addr)
        test_topic = "test_topic"
        test_payload = {"test": "TEST"}
        await admin_server.send_webhook(test_topic, test_payload)
        await asyncio.wait_for(admin_server.complete_webhooks(), 5.0)
        assert self.hook_results == [(test_topic, test_payload)]
