from unittest import IsolatedAsyncioTestCase
from aries_cloudagent.tests import mock

from .....admin.request_context import AdminRequestContext

from .. import routes as test_module


class TestTrustpingRoutes(IsolatedAsyncioTestCase):
    def setUp(self):
        self.session_inject = {}
        self.context = AdminRequestContext.test_context(self.session_inject)
        self.request_dict = {
            "context": self.context,
            "outbound_message_router": mock.CoroutineMock(),
        }
        self.request = mock.MagicMock(
            app={},
            match_info={},
            query={},
            __getitem__=lambda _, k: self.request_dict[k],
        )

    async def test_connections_send_ping(self):
        self.request.json = mock.CoroutineMock(return_value={"comment": "some comment"})
        self.request.match_info = {"conn_id": "dummy"}

        with mock.patch.object(
            test_module.ConnRecord, "retrieve_by_id", mock.CoroutineMock()
        ) as mock_retrieve, mock.patch.object(
            test_module, "Ping", mock.MagicMock()
        ) as mock_ping, mock.patch.object(
            test_module.web, "json_response", mock.MagicMock()
        ) as json_response:
            mock_ping.return_value = mock.MagicMock(_thread_id="dummy")
            mock_retrieve.return_value = mock.MagicMock(is_ready=True)
            result = await test_module.connections_send_ping(self.request)
            json_response.assert_called_once_with({"thread_id": "dummy"})
            assert result is json_response.return_value

    async def test_connections_send_ping_no_conn(self):
        self.request.json = mock.CoroutineMock(return_value={"comment": "some comment"})
        self.request.match_info = {"conn_id": "dummy"}

        with mock.patch.object(
            test_module.ConnRecord, "retrieve_by_id", mock.CoroutineMock()
        ) as mock_retrieve, mock.patch.object(
            test_module.web, "json_response", mock.MagicMock()
        ) as json_response:
            mock_retrieve.side_effect = test_module.StorageNotFoundError()
            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.connections_send_ping(self.request)

    async def test_connections_send_ping_not_ready(self):
        self.request.json = mock.CoroutineMock(return_value={"comment": "some comment"})
        self.request.match_info = {"conn_id": "dummy"}

        with mock.patch.object(
            test_module.ConnRecord, "retrieve_by_id", mock.CoroutineMock()
        ) as mock_retrieve, mock.patch.object(
            test_module.web, "json_response", mock.MagicMock()
        ) as json_response:
            mock_retrieve.return_value = mock.MagicMock(is_ready=False)
            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.connections_send_ping(self.request)

    async def test_register(self):
        mock_app = mock.MagicMock()
        mock_app.add_routes = mock.MagicMock()

        await test_module.register(mock_app)
        mock_app.add_routes.assert_called_once()

    async def test_post_process_routes(self):
        mock_app = mock.MagicMock(_state={"swagger_dict": {}})
        test_module.post_process_routes(mock_app)
        assert "tags" in mock_app._state["swagger_dict"]
