from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from .....admin.request_context import AdminRequestContext
from .....storage.error import StorageNotFoundError

from .. import routes as test_module


class TestBasicMessageRoutes(AsyncTestCase):
    async def setUp(self):
        self.session_inject = {}
        self.context = AdminRequestContext.test_context(self.session_inject)
        self.request_dict = {
            "context": self.context,
            "outbound_message_router": async_mock.CoroutineMock(),
        }
        self.request = async_mock.MagicMock(
            app={},
            match_info={},
            query={},
            __getitem__=lambda _, k: self.request_dict[k],
        )
        self.test_conn_id = "connection-id"

    async def test_connections_send_message(self):
        self.request.json = async_mock.CoroutineMock()
        self.request.match_info = {"conn_id": self.test_conn_id}

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "BasicMessage", autospec=True
        ) as mock_basic_message, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock()

            res = await test_module.connections_send_message(self.request)
            mock_response.assert_called_once_with({})
            mock_basic_message.assert_called_once()

    async def test_connections_send_message_no_conn_record(self):
        self.request.json = async_mock.CoroutineMock()
        self.request.match_info = {"conn_id": self.test_conn_id}

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "BasicMessage", autospec=True
        ) as mock_basic_message:
            # Emulate storage not found (bad connection id)
            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=StorageNotFoundError
            )

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.connections_send_message(self.request)

    async def test_connections_send_message_not_ready(self):
        self.request.json = async_mock.CoroutineMock()
        self.request.match_info = {"conn_id": self.test_conn_id}

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "BasicMessage", autospec=True
        ) as mock_basic_message:
            # Emulate connection not ready
            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock()
            mock_connection_record.retrieve_by_id.return_value.is_ready = False

            await test_module.connections_send_message(self.request)
            mock_basic_message.assert_not_called()

    async def test_register(self):
        mock_app = async_mock.MagicMock()
        mock_app.add_routes = async_mock.MagicMock()

        await test_module.register(mock_app)
        mock_app.add_routes.assert_called_once()

    async def test_post_process_routes(self):
        mock_app = async_mock.MagicMock(_state={"swagger_dict": {}})
        test_module.post_process_routes(mock_app)
        assert "tags" in mock_app._state["swagger_dict"]
