from aiohttp import ClientSession, DummyCookieJar, TCPConnector, web
from aiohttp.test_utils import unused_port

from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from ...config.default_context import DefaultContextBuilder
from ...config.injection_context import InjectionContext
from ...core.in_memory import InMemoryProfile
from ...core.protocol_registry import ProtocolRegistry
from ...transport.outbound.message import OutboundMessage
from ...utils.stats import Collector
from ...utils.task_queue import TaskQueue

from .. import server as test_module
from ..server import AdminServer, AdminSetupError


class TestAdminServer(AsyncTestCase):
    async def setUp(self):
        self.message_results = []
        self.webhook_results = []
        self.port = 0

        self.connector = TCPConnector(limit=16, limit_per_host=4)
        session_args = {"cookie_jar": DummyCookieJar(), "connector": self.connector}
        self.client_session = ClientSession(
            cookie_jar=DummyCookieJar(), connector=self.connector
        )

    async def tearDown(self):
        if self.client_session:
            await self.client_session.close()
            self.client_session = None

    async def test_debug_middleware(self):
        with async_mock.patch.object(
            test_module, "LOGGER", async_mock.MagicMock()
        ) as mock_logger:
            mock_logger.isEnabledFor = async_mock.MagicMock(return_value=True)
            mock_logger.debug = async_mock.MagicMock()

            request = async_mock.MagicMock(
                method="GET",
                path_qs="/hello/world?a=1&b=2",
                match_info={"match": "info"},
                text=async_mock.CoroutineMock(return_value="abc123"),
            )
            handler = async_mock.CoroutineMock()

            await test_module.debug_middleware(request, handler)
            mock_logger.isEnabledFor.assert_called_once()
            assert mock_logger.debug.call_count == 3

    async def test_ready_middleware(self):
        with async_mock.patch.object(
            test_module, "LOGGER", async_mock.MagicMock()
        ) as mock_logger:
            mock_logger.isEnabledFor = async_mock.MagicMock(return_value=True)
            mock_logger.debug = async_mock.MagicMock()
            mock_logger.info = async_mock.MagicMock()
            mock_logger.error = async_mock.MagicMock()

            request = async_mock.MagicMock(
                rel_url="/", app=async_mock.MagicMock(_state={"ready": False})
            )
            handler = async_mock.CoroutineMock(return_value="OK")
            with self.assertRaises(test_module.web.HTTPServiceUnavailable):
                await test_module.ready_middleware(request, handler)

            request.app._state["ready"] = True
            assert await test_module.ready_middleware(request, handler) == "OK"

            request.app._state["ready"] = True
            handler = async_mock.CoroutineMock(
                side_effect=test_module.LedgerConfigError("Bad config")
            )
            with self.assertRaises(test_module.LedgerConfigError):
                await test_module.ready_middleware(request, handler)

            request.app._state["ready"] = True
            handler = async_mock.CoroutineMock(
                side_effect=test_module.web.HTTPFound(location="/api/doc")
            )
            with self.assertRaises(test_module.web.HTTPFound):
                await test_module.ready_middleware(request, handler)

            request.app._state["ready"] = True
            handler = async_mock.CoroutineMock(
                side_effect=test_module.asyncio.CancelledError("Cancelled")
            )
            with self.assertRaises(test_module.asyncio.CancelledError):
                await test_module.ready_middleware(request, handler)

            request.app._state["ready"] = True
            handler = async_mock.CoroutineMock(side_effect=KeyError("No such thing"))
            with self.assertRaises(KeyError):
                await test_module.ready_middleware(request, handler)

    def get_admin_server(
        self, settings: dict = None, context: InjectionContext = None
    ) -> AdminServer:
        if not context:
            context = InjectionContext()
        if settings:
            context.update_settings(settings)

        # middleware is task queue xor collector: cover both over test suite
        task_queue = (settings or {}).pop("task_queue", None)

        plugin_registry = async_mock.MagicMock(
            test_module.PluginRegistry, autospec=True
        )
        plugin_registry.post_process_routes = async_mock.MagicMock()
        context.injector.bind_instance(test_module.PluginRegistry, plugin_registry)

        collector = Collector()
        context.injector.bind_instance(test_module.Collector, collector)

        profile = InMemoryProfile.test_profile()

        self.port = unused_port()
        return AdminServer(
            "0.0.0.0",
            self.port,
            context,
            profile,
            self.outbound_message_router,
            self.webhook_router,
            conductor_stop=async_mock.CoroutineMock(),
            task_queue=TaskQueue(max_active=4) if task_queue else None,
            conductor_stats=(
                None if task_queue else async_mock.CoroutineMock(return_value=[1, 2])
            ),
        )

    async def outbound_message_router(self, *args):
        self.message_results.append(args)

    def webhook_router(self, *args):
        self.webhook_results.append(args)

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
        with async_mock.patch.object(
            server, "websocket_queues", async_mock.MagicMock()
        ) as mock_wsq:
            mock_wsq.values = async_mock.MagicMock(
                return_value=[async_mock.MagicMock(stop=async_mock.MagicMock())]
            )
            await server.stop()

        with async_mock.patch.object(
            web.TCPSite, "start", async_mock.CoroutineMock()
        ) as mock_start:
            mock_start.side_effect = OSError("Failure to launch")
            with self.assertRaises(AdminSetupError):
                await self.get_admin_server(settings).start()

    async def test_responder_send(self):
        message = OutboundMessage(payload="{}")
        server = self.get_admin_server()
        await server.responder.send_outbound(message)
        assert self.message_results == [(server.context, message)]

    async def test_responder_webhook(self):
        server = self.get_admin_server()
        test_url = "target_url"
        test_attempts = 99
        server.add_webhook_target(
            target_url=test_url,
            topic_filter=["*"],  # cover vacuous filter
            max_attempts=test_attempts,
        )
        test_topic = "test_topic"
        test_payload = {"test": "TEST"}

        with async_mock.patch.object(
            server, "websocket_queues", async_mock.MagicMock()
        ) as mock_wsq:
            mock_wsq.values = async_mock.MagicMock(
                return_value=[
                    async_mock.MagicMock(
                        authenticated=True, enqueue=async_mock.CoroutineMock()
                    )
                ]
            )

            await server.responder.send_webhook(test_topic, test_payload)
            assert self.webhook_results == [
                (test_topic, test_payload, test_url, test_attempts)
            ]

        server.remove_webhook_target(target_url=test_url)
        assert test_url not in server.webhook_targets

    async def test_import_routes(self):
        # this test just imports all default admin routes
        # for routes with associated tests, this shouldn't make a difference in coverage
        context = InjectionContext()
        context.injector.bind_instance(ProtocolRegistry, ProtocolRegistry())
        await DefaultContextBuilder().load_plugins(context)
        server = self.get_admin_server({"admin.admin_insecure_mode": True}, context)
        app = await server.make_application()

    async def test_register_external_plugin_x(self):
        context = InjectionContext()
        context.injector.bind_instance(ProtocolRegistry, ProtocolRegistry())
        with self.assertRaises(ValueError):
            builder = DefaultContextBuilder(
                settings={"external_plugins": "aries_cloudagent.nosuchmodule"}
            )
            await builder.load_plugins(context)

    async def test_visit_insecure_mode(self):
        settings = {"admin.admin_insecure_mode": True, "task_queue": True}
        server = self.get_admin_server(settings)
        await server.start()

        async with self.client_session.post(
            f"http://127.0.0.1:{self.port}/status/reset", headers={}
        ) as response:
            assert response.status == 200

        async with self.client_session.ws_connect(
            f"http://127.0.0.1:{self.port}/ws"
        ) as ws:
            result = await ws.receive_json()
            assert result["topic"] == "settings"

        for path in (
            "",
            "plugins",
            "status",
            "status/live",
            "status/ready",
            "shutdown",  # mock conductor has magic-mock stop()
        ):
            async with self.client_session.get(
                f"http://127.0.0.1:{self.port}/{path}", headers={}
            ) as response:
                assert response.status == 200

        await server.stop()

    async def test_visit_secure_mode(self):
        settings = {
            "admin.admin_insecure_mode": False,
            "admin.admin_api_key": "test-api-key",
        }
        server = self.get_admin_server(settings)
        await server.start()

        async with self.client_session.get(
            f"http://127.0.0.1:{self.port}/status", headers={"x-api-key": "wrong-key"}
        ) as response:
            assert response.status == 401

        async with self.client_session.get(
            f"http://127.0.0.1:{self.port}/status",
            headers={"x-api-key": "test-api-key"},
        ) as response:
            assert response.status == 200

        async with self.client_session.ws_connect(
            f"http://127.0.0.1:{self.port}/ws", headers={"x-api-key": "test-api-key"}
        ) as ws:
            result = await ws.receive_json()
            assert result["topic"] == "settings"

        await server.stop()

    async def test_visit_shutting_down(self):
        settings = {
            "admin.admin_insecure_mode": True,
        }
        server = self.get_admin_server(settings)
        await server.start()

        async with self.client_session.get(
            f"http://127.0.0.1:{self.port}/shutdown", headers={}
        ) as response:
            assert response.status == 200

        async with self.client_session.get(
            f"http://127.0.0.1:{self.port}/status", headers={}
        ) as response:
            assert response.status == 503

        async with self.client_session.get(
            f"http://127.0.0.1:{self.port}/status/live", headers={}
        ) as response:
            assert response.status == 200
        await server.stop()

    async def test_server_health_state(self):
        settings = {
            "admin.admin_insecure_mode": True,
        }
        server = self.get_admin_server(settings)
        await server.start()

        async with self.client_session.get(
            f"http://127.0.0.1:{self.port}/status/live", headers={}
        ) as response:
            assert response.status == 200
            response_json = await response.json()
            assert response_json["alive"]

        async with self.client_session.get(
            f"http://127.0.0.1:{self.port}/status/ready", headers={}
        ) as response:
            assert response.status == 200
            response_json = await response.json()
            assert response_json["ready"]

        server.notify_fatal_error()
        async with self.client_session.get(
            f"http://127.0.0.1:{self.port}/status/live", headers={}
        ) as response:
            assert response.status == 503

        async with self.client_session.get(
            f"http://127.0.0.1:{self.port}/status/ready", headers={}
        ) as response:
            assert response.status == 503
        await server.stop()
