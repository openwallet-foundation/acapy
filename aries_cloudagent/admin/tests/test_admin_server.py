import json

import pytest
import mock as async_mock
from async_case import IsolatedAsyncioTestCase

from aiohttp import ClientSession, DummyCookieJar, TCPConnector, web
from aiohttp.test_utils import unused_port

from ...config.default_context import DefaultContextBuilder
from ...config.injection_context import InjectionContext
from ...core.event_bus import Event
from ...core.in_memory import InMemoryProfile
from ...core.protocol_registry import ProtocolRegistry
from ...core.goal_code_registry import GoalCodeRegistry
from ...utils.stats import Collector
from ...utils.task_queue import TaskQueue

from .. import server as test_module
from ..server import AdminServer, AdminSetupError


class TestAdminServer(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.message_results = []
        self.webhook_results = []
        self.port = 0

        self.connector = TCPConnector(limit=16, limit_per_host=4)
        self.client_session = ClientSession(
            cookie_jar=DummyCookieJar(), connector=self.connector
        )

    async def asyncTearDown(self):
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
                text=async_mock.AsyncMock(return_value="abc123"),
            )
            handler = async_mock.AsyncMock()

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
            handler = async_mock.AsyncMock(return_value="OK")
            with self.assertRaises(test_module.web.HTTPServiceUnavailable):
                await test_module.ready_middleware(request, handler)

            request.app._state["ready"] = True
            assert await test_module.ready_middleware(request, handler) == "OK"

            request.app._state["ready"] = True
            handler = async_mock.AsyncMock(
                side_effect=test_module.LedgerConfigError("Bad config")
            )
            with self.assertRaises(test_module.LedgerConfigError):
                await test_module.ready_middleware(request, handler)

            request.app._state["ready"] = True
            handler = async_mock.AsyncMock(
                side_effect=test_module.web.HTTPFound(location="/api/doc")
            )
            with self.assertRaises(test_module.web.HTTPFound):
                await test_module.ready_middleware(request, handler)

            request.app._state["ready"] = True
            handler = async_mock.AsyncMock(
                side_effect=test_module.asyncio.CancelledError("Cancelled")
            )
            with self.assertRaises(test_module.asyncio.CancelledError):
                await test_module.ready_middleware(request, handler)

            request.app._state["ready"] = True
            handler = async_mock.AsyncMock(side_effect=KeyError("No such thing"))
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
            conductor_stop=async_mock.AsyncMock(),
            task_queue=TaskQueue(max_active=4) if task_queue else None,
            conductor_stats=(
                None if task_queue else async_mock.AsyncMock(return_value={"a": 1})
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
            "admin.admin_client_max_request_size": 4,
            "admin.admin_api_key": "test-api-key",
        }
        server = self.get_admin_server(settings)
        await server.start()
        assert server.app._client_max_size == 4 * 1024 * 1024
        with async_mock.patch.object(
            server, "websocket_queues", async_mock.MagicMock()
        ) as mock_wsq:
            mock_wsq.values = async_mock.MagicMock(
                return_value=[async_mock.MagicMock(stop=async_mock.MagicMock())]
            )
            await server.stop()

        with async_mock.patch.object(
            web.TCPSite, "start", async_mock.AsyncMock()
        ) as mock_start:
            mock_start.side_effect = OSError("Failure to launch")
            with self.assertRaises(AdminSetupError):
                await self.get_admin_server(settings).start()

    async def test_import_routes(self):
        # this test just imports all default admin routes
        # for routes with associated tests, this shouldn't make a difference in coverage
        context = InjectionContext()
        context.injector.bind_instance(ProtocolRegistry, ProtocolRegistry())
        context.injector.bind_instance(GoalCodeRegistry, GoalCodeRegistry())
        await DefaultContextBuilder().load_plugins(context)
        server = self.get_admin_server({"admin.admin_insecure_mode": True}, context)
        app = await server.make_application()

    async def test_import_routes_multitenant_middleware(self):
        # imports all default admin routes
        context = InjectionContext(
            settings={"multitenant.base_wallet_routes": ["/test"]}
        )
        context.injector.bind_instance(ProtocolRegistry, ProtocolRegistry())
        context.injector.bind_instance(GoalCodeRegistry, GoalCodeRegistry())
        context.injector.bind_instance(
            test_module.BaseMultitenantManager,
            async_mock.MagicMock(spec=test_module.BaseMultitenantManager),
        )
        await DefaultContextBuilder().load_plugins(context)
        server = self.get_admin_server(
            {
                "admin.admin_insecure_mode": False,
                "admin.admin_api_key": "test-api-key",
            },
            context,
        )

        # cover multitenancy start code
        app = await server.make_application()
        app["swagger_dict"] = {}
        await server.on_startup(app)

        # multitenant authz
        [mt_authz_middle] = [
            m for m in app.middlewares if ".check_multitenant_authorization" in str(m)
        ]

        mock_request = async_mock.MagicMock(
            method="GET",
            headers={"Authorization": "Bearer ..."},
            path="/multitenancy/etc",
            text=async_mock.AsyncMock(return_value="abc123"),
        )
        with self.assertRaises(test_module.web.HTTPUnauthorized):
            await mt_authz_middle(mock_request, None)

        mock_request = async_mock.MagicMock(
            method="GET",
            headers={},
            path="/protected/non-multitenancy/non-server",
            text=async_mock.AsyncMock(return_value="abc123"),
        )
        with self.assertRaises(test_module.web.HTTPUnauthorized):
            await mt_authz_middle(mock_request, None)

        mock_request = async_mock.MagicMock(
            method="GET",
            headers={"Authorization": "Bearer ..."},
            path="/protected/non-multitenancy/non-server",
            text=async_mock.AsyncMock(return_value="abc123"),
        )
        mock_handler = async_mock.AsyncMock()
        await mt_authz_middle(mock_request, mock_handler)
        assert mock_handler.called_once_with(mock_request)

        mock_request = async_mock.MagicMock(
            method="GET",
            headers={"Authorization": "Non-bearer ..."},
            path="/test",
            text=async_mock.AsyncMock(return_value="abc123"),
        )
        mock_handler = async_mock.AsyncMock()
        await mt_authz_middle(mock_request, mock_handler)
        assert mock_handler.called_once_with(mock_request)

        # multitenant setup context exception paths
        [setup_ctx_middle] = [m for m in app.middlewares if ".setup_context" in str(m)]

        mock_request = async_mock.MagicMock(
            method="GET",
            headers={"Authorization": "Non-bearer ..."},
            path="/protected/non-multitenancy/non-server",
            text=async_mock.AsyncMock(return_value="abc123"),
        )
        with self.assertRaises(test_module.web.HTTPUnauthorized):
            await setup_ctx_middle(mock_request, None)

        mock_request = async_mock.MagicMock(
            method="GET",
            headers={"Authorization": "Bearer ..."},
            path="/protected/non-multitenancy/non-server",
            text=async_mock.AsyncMock(return_value="abc123"),
        )
        with async_mock.patch.object(
            server.multitenant_manager,
            "get_profile_for_token",
            async_mock.AsyncMock(),
        ) as mock_get_profile:
            mock_get_profile.side_effect = [
                test_module.MultitenantManagerError("corrupt token"),
                test_module.StorageNotFoundError("out of memory"),
            ]
            for i in range(2):
                with self.assertRaises(test_module.web.HTTPUnauthorized):
                    await setup_ctx_middle(mock_request, None)

    async def test_register_external_plugin_x(self):
        context = InjectionContext()
        context.injector.bind_instance(ProtocolRegistry, ProtocolRegistry())
        context.injector.bind_instance(GoalCodeRegistry, GoalCodeRegistry())
        with self.assertLogs(level="ERROR") as logs:
            builder = DefaultContextBuilder(
                settings={"external_plugins": ["aries_cloudagent.nosuchmodule"]}
            )
            await builder.load_plugins(context)
        assert "Module doesn't exist: aries_cloudagent.nosuchmodule" in "\n".join(
            logs.output
        )

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

    @pytest.mark.skip(reason="async_case library not compatible with python 3.10")
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

        # Make sure that OPTIONS requests used by browsers for CORS
        # are allowed without a x-api-key even when x-api-key security is enabled
        async with self.client_session.options(
            f"http://127.0.0.1:{self.port}/status",
            headers={
                "Access-Control-Request-Headers": "x-api-key",
                "Access-Control-Request-Method": "GET",
                "Connection": "keep-alive",
                "Host": f"http://127.0.0.1:{self.port}/status",
                "Origin": "http://localhost:3000",
                "Referer": "http://localhost:3000/",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-site",
            },
        ) as response:
            assert response.status == 200
            assert response.headers["Access-Control-Allow-Credentials"] == "true"
            assert response.headers["Access-Control-Allow-Headers"] == "X-API-KEY"
            assert response.headers["Access-Control-Allow-Methods"] == "GET"
            assert (
                response.headers["Access-Control-Allow-Origin"]
                == "http://localhost:3000"
            )

        async with self.client_session.ws_connect(
            f"http://127.0.0.1:{self.port}/ws", headers={"x-api-key": "test-api-key"}
        ) as ws:
            result = await ws.receive_json()
            assert result["topic"] == "settings"

        await server.stop()

    @pytest.mark.skip(reason="async_case library not compatible with python 3.10")
    async def test_query_config(self):
        settings = {
            "admin.admin_insecure_mode": False,
            "admin.admin_api_key": "test-api-key",
            "admin.webhook_urls": ["localhost:8123/abc#secret", "localhost:8123/def"],
            "multitenant.jwt_secret": "abc123",
            "wallet.key": "abc123",
            "wallet.rekey": "def456",
            "wallet.seed": "00000000000000000000000000000000",
            "wallet.storage.creds": "secret",
        }
        server = self.get_admin_server(settings)
        await server.start()

        async with self.client_session.get(
            f"http://127.0.0.1:{self.port}/status/config",
            headers={"x-api-key": "test-api-key"},
        ) as response:
            config = json.loads(await response.text())["config"]
            assert "admin.admin_insecure_mode" in config
            assert all(
                k not in config
                for k in [
                    "admin.admin_api_key",
                    "multitenant.jwt_secret",
                    "wallet.key",
                    "wallet.rekey",
                    "wallet.seed",
                    "wallet.storage_creds",
                ]
            )
            assert config["admin.webhook_urls"] == [
                "localhost:8123/abc",
                "localhost:8123/def",
            ]

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


@pytest.fixture
async def server():
    test_class = TestAdminServer()
    await test_class.asyncSetUp()
    yield test_class.get_admin_server()
    await test_class.asyncTearDown()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "event_topic, webhook_topic",
    [("acapy::record::topic", "topic"), ("acapy::record::topic::state", "topic")],
)
async def test_on_record_event(server, event_topic, webhook_topic):
    profile = InMemoryProfile.test_profile()
    with async_mock.patch.object(
        server, "send_webhook", async_mock.AsyncMock()
    ) as mock_send_webhook:
        await server._on_record_event(profile, Event(event_topic, None))
        mock_send_webhook.assert_called_once_with(profile, webhook_topic, None)


@pytest.mark.asyncio
async def test_admin_responder_profile_expired_x():
    def _smaller_scope():
        profile = InMemoryProfile.test_profile()
        return test_module.AdminResponder(profile, None)

    responder = _smaller_scope()
    with pytest.raises(RuntimeError):
        await responder.send_outbound(None)

    with pytest.raises(RuntimeError):
        await responder.send_webhook("test", {})
