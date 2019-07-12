from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from .. import routes as test_module

from ....storage.error import StorageNotFoundError


class TestBasicMessageRoutes(AsyncTestCase):
    async def test_connections_send_message(self):
        mock_request = async_mock.MagicMock()
        mock_request.json = async_mock.CoroutineMock()

        mock_request.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": "context",
        }

        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "BasicMessage", autospec=True
        ) as mock_basic_message, async_mock.patch.object(
            test_module, "ConnectionManager", autospec=True
        ) as mock_conn_manager:

            mock_conn_manager.return_value.log_activity = async_mock.CoroutineMock()

            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock()

            test_module.web.json_response = async_mock.CoroutineMock()

            res = await test_module.connections_send_message(mock_request)
            test_module.web.json_response.assert_called_once_with({})
            mock_conn_manager.return_value.log_activity.assert_called_once_with(
                mock_connection_record.retrieve_by_id.return_value,
                "message",
                mock_connection_record.retrieve_by_id.return_value.DIRECTION_SENT,
                {"content": mock_request.json.return_value["content"]},
            )
            mock_basic_message.assert_called_once()

    async def test_connections_send_message_no_conn_record(self):
        mock_request = async_mock.MagicMock()
        mock_request.json = async_mock.CoroutineMock()

        mock_request.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": "context",
        }

        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "BasicMessage", autospec=True
        ) as mock_basic_message, async_mock.patch.object(
            test_module, "ConnectionManager", autospec=True
        ) as mock_conn_manager:

            # Emulate storage not found (bad connection id)
            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=StorageNotFoundError
            )

            mock_conn_manager.return_value.log_activity = async_mock.CoroutineMock()

            test_module.web.json_response = async_mock.CoroutineMock()

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.connections_send_message(mock_request)

    async def test_connections_send_message_not_ready(self):
        mock_request = async_mock.MagicMock()
        mock_request.json = async_mock.CoroutineMock()

        mock_request.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": "context",
        }

        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "BasicMessage", autospec=True
        ) as mock_basic_message, async_mock.patch.object(
            test_module, "ConnectionManager", autospec=True
        ) as mock_conn_manager:

            # Emulate connection not ready
            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock()
            mock_connection_record.retrieve_by_id.return_value.is_ready = False

            mock_conn_manager.return_value.log_activity = async_mock.CoroutineMock()

            test_module.web.json_response = async_mock.CoroutineMock()

            await test_module.connections_send_message(mock_request)
            mock_basic_message.assert_not_called()
