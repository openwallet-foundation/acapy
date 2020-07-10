from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock
import pytest

from aiohttp.web import HTTPBadRequest, HTTPForbidden, HTTPNotFound

from .. import routes as test_module


class TestOutOfBandRoutes(AsyncTestCase):
    async def test_invitation_create(self):
        request = async_mock.MagicMock()
        request.app = {"request_context": async_mock.MagicMock()}
        request.query = {"multi_use": "true"}
        request.json = async_mock.CoroutineMock(
            return_value={
                "attachments": async_mock.MagicMock(),
                "include_handshake": True,
                "use_public_did": True,
            }
        )

        with async_mock.patch.object(
            test_module, "OutOfBandManager", autospec=True
        ) as mock_oob_mgr, async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as mock_json_response:
            mock_oob_mgr.return_value.create_invitation = async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(
                    serialize=async_mock.MagicMock(return_value={"abc": "123"})
                )
            )

            result = await test_module.invitation_create(request)
            mock_json_response.assert_called_once_with({"abc": "123"})

    async def test_invitation_create_x(self):
        request = async_mock.MagicMock()
        request.app = {"request_context": async_mock.MagicMock()}
        request.query = {"multi_use": "true"}
        request.json = async_mock.CoroutineMock(
            return_value={
                "attachments": async_mock.MagicMock(),
                "include_handshake": True,
                "use_public_did": True,
            }
        )

        with async_mock.patch.object(
            test_module, "OutOfBandManager", autospec=True
        ) as mock_oob_mgr, async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as mock_json_response:
            mock_oob_mgr.return_value.create_invitation = async_mock.CoroutineMock(
                side_effect=test_module.OutOfBandManagerError()
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.invitation_create(request)
            mock_json_response.assert_not_called()

    async def test_invitation_receive(self):
        request = async_mock.MagicMock()
        request.app = {"request_context": async_mock.MagicMock()}
        request.json = async_mock.CoroutineMock()

        with async_mock.patch.object(
            test_module, "OutOfBandManager", autospec=True
        ) as mock_oob_mgr, async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as mock_json_response:
            mock_oob_mgr.return_value.receive_invitation = async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(
                    serialize=async_mock.MagicMock(return_value={"abc": "123"})
                )
            )

            result = await test_module.invitation_receive(request)
            mock_json_response.assert_called_once_with({"abc": "123"})

    async def test_register(self):
        mock_app = async_mock.MagicMock()
        mock_app.add_routes = async_mock.MagicMock()

        await test_module.register(mock_app)
        mock_app.add_routes.assert_called_once()

    async def test_post_process_routes(self):
        mock_app = async_mock.MagicMock(_state={"swagger_dict": {}})
        test_module.post_process_routes(mock_app)
        assert "tags" in mock_app._state["swagger_dict"]
