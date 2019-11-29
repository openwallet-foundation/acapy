from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from ....storage.error import StorageNotFoundError

from .. import routes as test_module


class TestActionMenuRoutes(AsyncTestCase):
    async def test_actionmenu_close(self):
        mock_request = async_mock.MagicMock()
        mock_request.json = async_mock.CoroutineMock()

        mock_request.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": "context",
        }

        test_module.retrieve_connection_menu = async_mock.CoroutineMock()
        test_module.save_connection_menu = async_mock.CoroutineMock()
        test_module.web.json_response = async_mock.CoroutineMock()

        res = await test_module.actionmenu_close(mock_request)
        test_module.web.json_response.assert_called_once_with({})

    async def test_actionmenu_close_not_found(self):
        mock_request = async_mock.MagicMock()
        mock_request.json = async_mock.CoroutineMock()

        mock_request.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": "context",
        }

        test_module.retrieve_connection_menu = async_mock.CoroutineMock(
            return_value=None
        )
        with self.assertRaises(test_module.web.HTTPNotFound):
            await test_module.actionmenu_close(mock_request)

    async def test_actionmenu_fetch(self):
        mock_request = async_mock.MagicMock()
        mock_request.json = async_mock.CoroutineMock()

        mock_request.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": "context",
        }

        test_module.retrieve_connection_menu = async_mock.CoroutineMock(
            return_value=None
        )
        test_module.web.json_response = async_mock.CoroutineMock()

        res = await test_module.actionmenu_fetch(mock_request)
        test_module.web.json_response.assert_called_once_with(
            {
                "result": None
            }
        )

    async def test_actionmenu_perform(self):
        mock_request = async_mock.MagicMock()
        mock_request.json = async_mock.CoroutineMock()

        mock_request.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": "context",
        }

        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "Perform", autospec=True
        ) as mock_perform:

            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock()

            test_module.web.json_response = async_mock.CoroutineMock()

            res = await test_module.actionmenu_perform(mock_request)
            test_module.web.json_response.assert_called_once_with({})
            mock_request.app["outbound_message_router"].assert_called_once_with(
                mock_perform.return_value, connection_id=mock_request.match_info["id"]
            )

    async def test_actionmenu_perform_no_conn_record(self):
        mock_request = async_mock.MagicMock()
        mock_request.json = async_mock.CoroutineMock()

        mock_request.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": "context",
        }

        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "Perform", autospec=True
        ) as mock_perform:

            # Emulate storage not found (bad connection id)
            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=StorageNotFoundError
            )

            test_module.web.json_response = async_mock.CoroutineMock()

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.actionmenu_perform(mock_request)

    async def test_actionmenu_perform_conn_not_ready(self):
        mock_request = async_mock.MagicMock()
        mock_request.json = async_mock.CoroutineMock()

        mock_request.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": "context",
        }

        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "Perform", autospec=True
        ) as mock_perform:

            # Emulate connection not ready
            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock()
            mock_connection_record.retrieve_by_id.return_value.is_ready = False

            test_module.web.json_response = async_mock.CoroutineMock()

            with self.assertRaises(test_module.web.HTTPForbidden):
                await test_module.actionmenu_perform(mock_request)

    async def test_actionmenu_request(self):
        mock_request = async_mock.MagicMock()
        mock_request.json = async_mock.CoroutineMock()

        mock_request.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": "context",
        }

        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "MenuRequest", autospec=True
        ) as menu_request:

            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock()

            test_module.web.json_response = async_mock.CoroutineMock()

            res = await test_module.actionmenu_request(mock_request)
            test_module.web.json_response.assert_called_once_with({})
            mock_request.app["outbound_message_router"].assert_called_once_with(
                menu_request.return_value, connection_id=mock_request.match_info["id"]
            )

    async def test_actionmenu_request_no_conn_record(self):
        mock_request = async_mock.MagicMock()
        mock_request.json = async_mock.CoroutineMock()

        mock_request.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": "context",
        }

        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "Perform", autospec=True
        ) as mock_perform:

            # Emulate storage not found (bad connection id)
            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=StorageNotFoundError
            )

            test_module.web.json_response = async_mock.CoroutineMock()

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.actionmenu_request(mock_request)

    async def test_actionmenu_request_conn_not_ready(self):
        mock_request = async_mock.MagicMock()
        mock_request.json = async_mock.CoroutineMock()

        mock_request.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": "context",
        }

        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "Perform", autospec=True
        ) as mock_perform:

            # Emulate connection not ready
            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock()
            mock_connection_record.retrieve_by_id.return_value.is_ready = False

            test_module.web.json_response = async_mock.CoroutineMock()

            with self.assertRaises(test_module.web.HTTPForbidden):
                await test_module.actionmenu_request(mock_request)

    async def test_actionmenu_send(self):
        mock_request = async_mock.MagicMock()
        mock_request.json = async_mock.CoroutineMock()

        mock_request.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": "context",
        }

        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "Menu", autospec=True
        ) as mock_menu:

            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock()
            test_module.web.json_response = async_mock.CoroutineMock()
            mock_menu.deserialize = async_mock.MagicMock()

            res = await test_module.actionmenu_send(mock_request)
            test_module.web.json_response.assert_called_once_with({})
            mock_request.app["outbound_message_router"].assert_called_once_with(
                mock_menu.deserialize.return_value,
                connection_id=mock_request.match_info["id"],
            )

    async def test_actionmenu_send_deserialize_x(self):
        mock_request = async_mock.MagicMock()
        mock_request.json = async_mock.CoroutineMock()

        mock_request.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": "context",
        }

        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "Menu", autospec=True
        ) as mock_menu:

            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock()
            test_module.web.json_response = async_mock.CoroutineMock()
            mock_menu.deserialize = async_mock.MagicMock(
                side_effect=ValueError("cannot deserialize")
            )

            with self.assertRaises(ValueError):
                await test_module.actionmenu_send(mock_request)

    async def test_actionmenu_send_no_conn_record(self):
        mock_request = async_mock.MagicMock()
        mock_request.json = async_mock.CoroutineMock()

        mock_request.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": "context",
        }

        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "Menu", autospec=True
        ) as mock_menu:

            mock_menu.deserialize = async_mock.MagicMock()

            # Emulate storage not found (bad connection id)
            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=StorageNotFoundError
            )

            test_module.web.json_response = async_mock.CoroutineMock()

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.actionmenu_send(mock_request)

    async def test_actionmenu_send_conn_not_ready(self):
        mock_request = async_mock.MagicMock()
        mock_request.json = async_mock.CoroutineMock()

        mock_request.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": "context",
        }

        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "Menu", autospec=True
        ) as mock_menu:

            mock_menu.deserialize = async_mock.MagicMock()

            # Emulate connection not ready
            mock_connection_record.retrieve_by_id = async_mock.CoroutineMock()
            mock_connection_record.retrieve_by_id.return_value.is_ready = False

            test_module.web.json_response = async_mock.CoroutineMock()

            with self.assertRaises(test_module.web.HTTPForbidden):
                await test_module.actionmenu_send(mock_request)

    async def test_register(self):
        mock_app = async_mock.MagicMock()
        mock_app.add_routes = async_mock.MagicMock()

        await test_module.register(mock_app)
        mock_app.add_routes.assert_called_once()

