from unittest import IsolatedAsyncioTestCase

from .....admin.request_context import AdminRequestContext
from .....connections.models.conn_record import ConnRecord
from .....storage.error import StorageError
from .....tests import mock
from .....utils.testing import create_test_profile
from .. import routes as test_module


class TestOutOfBandRoutes(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.profile = await create_test_profile(
            settings={
                "admin.admin_api_key": "secret-key",
            }
        )
        self.context = AdminRequestContext.test_context({}, profile=self.profile)
        self.request_dict = {
            "context": self.context,
            "outbound_message_router": mock.CoroutineMock(),
        }
        self.request = mock.MagicMock(
            app={},
            match_info={},
            query={},
            __getitem__=lambda _, k: self.request_dict[k],
            headers={"x-api-key": "secret-key"},
        )

    async def test_invitation_create(self):
        self.request.query = {
            "multi_use": "true",
            "auto_accept": "true",
        }
        body = {
            "attachments": mock.MagicMock(),
            "handshake_protocols": [test_module.HSProto.RFC23.name],
            "use_public_did": True,
            "metadata": {"hello": "world"},
        }
        self.request.json = mock.CoroutineMock(return_value=body)

        with (
            mock.patch.object(
                test_module, "OutOfBandManager", autospec=True
            ) as mock_oob_mgr,
            mock.patch.object(
                test_module.web, "json_response", mock.Mock()
            ) as mock_json_response,
        ):
            mock_oob_mgr.return_value.create_invitation = mock.CoroutineMock(
                return_value=mock.MagicMock(
                    serialize=mock.MagicMock(return_value={"abc": "123"})
                )
            )

            await test_module.invitation_create(self.request)
            mock_oob_mgr.return_value.create_invitation.assert_called_once_with(
                my_label=None,
                auto_accept=True,
                public=True,
                use_did_method=None,
                use_did=None,
                multi_use=True,
                create_unique_did=False,
                hs_protos=[test_module.HSProto.RFC23],
                attachments=body["attachments"],
                metadata=body["metadata"],
                alias=None,
                mediation_id=None,
                service_accept=None,
                protocol_version=None,
                goal_code=None,
                goal=None,
            )
            mock_json_response.assert_called_once_with({"abc": "123"})

    async def test_invitation_remove(self):
        self.request.match_info = {"invi_msg_id": "dummy"}

        with (
            mock.patch.object(
                test_module, "OutOfBandManager", autospec=True
            ) as mock_oob_mgr,
            mock.patch.object(
                test_module.web, "json_response", mock.Mock()
            ) as mock_json_response,
        ):
            mock_oob_mgr.return_value.delete_conn_and_oob_record_invitation = (
                mock.CoroutineMock(return_value=None)
            )
            await test_module.invitation_remove(self.request)
            mock_json_response.assert_called_once_with({})

    async def test_invitation_create_with_accept(self):
        self.request.query = {
            "multi_use": "true",
            "auto_accept": "true",
        }
        body = {
            "attachments": mock.MagicMock(),
            "handshake_protocols": [test_module.HSProto.RFC23.name],
            "accept": ["didcomm/aip1", "didcomm/aip2;env=rfc19"],
            "use_public_did": True,
            "metadata": {"hello": "world"},
        }
        self.request.json = mock.CoroutineMock(return_value=body)

        with (
            mock.patch.object(
                test_module, "OutOfBandManager", autospec=True
            ) as mock_oob_mgr,
            mock.patch.object(
                test_module.web, "json_response", mock.Mock()
            ) as mock_json_response,
        ):
            mock_oob_mgr.return_value.create_invitation = mock.CoroutineMock(
                return_value=mock.MagicMock(
                    serialize=mock.MagicMock(return_value={"abc": "123"})
                )
            )

            await test_module.invitation_create(self.request)
            mock_oob_mgr.return_value.create_invitation.assert_called_once_with(
                my_label=None,
                auto_accept=True,
                public=True,
                use_did_method=None,
                use_did=None,
                multi_use=True,
                create_unique_did=False,
                hs_protos=[test_module.HSProto.RFC23],
                attachments=body["attachments"],
                metadata=body["metadata"],
                alias=None,
                mediation_id=None,
                service_accept=["didcomm/aip1", "didcomm/aip2;env=rfc19"],
                protocol_version=None,
                goal_code=None,
                goal=None,
            )
            mock_json_response.assert_called_once_with({"abc": "123"})

    async def test_invitation_create_x(self):
        self.request.query = {"multi_use": "true"}
        self.request.json = mock.CoroutineMock(
            return_value={
                "attachments": mock.MagicMock(),
                "handshake_protocols": [23],
                "use_public_did": True,
            }
        )

        with (
            mock.patch.object(
                test_module, "OutOfBandManager", autospec=True
            ) as mock_oob_mgr,
            mock.patch.object(
                test_module.web, "json_response", mock.Mock()
            ) as mock_json_response,
        ):
            mock_oob_mgr.return_value.create_invitation = mock.CoroutineMock(
                side_effect=test_module.OutOfBandManagerError()
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.invitation_create(self.request)
            mock_json_response.assert_not_called()

    async def test_invitation_receive(self):
        self.request.json = mock.CoroutineMock()
        expected_connection_record = ConnRecord(connection_id="some-id")

        with (
            mock.patch.object(
                test_module, "OutOfBandManager", autospec=True
            ) as mock_oob_mgr,
            mock.patch.object(test_module.InvitationMessage, "deserialize", mock.Mock()),
            mock.patch.object(
                test_module.web, "json_response", mock.Mock()
            ) as mock_json_response,
        ):
            mock_oob_mgr.return_value.receive_invitation = mock.CoroutineMock(
                return_value=expected_connection_record
            )

            await test_module.invitation_receive(self.request)
            mock_json_response.assert_called_once_with(
                expected_connection_record.serialize()
            )

    async def test_invitation_receive_forbidden_x(self):
        self.context.update_settings({"admin.no_receive_invites": True})
        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.invitation_receive(self.request)

    async def test_invitation_receive_x(self):
        self.request.json = mock.CoroutineMock()

        with (
            mock.patch.object(
                test_module, "OutOfBandManager", autospec=True
            ) as mock_oob_mgr,
            mock.patch.object(test_module.InvitationMessage, "deserialize", mock.Mock()),
            mock.patch.object(test_module.web, "json_response", mock.Mock()),
        ):
            mock_oob_mgr.return_value.receive_invitation = mock.CoroutineMock(
                side_effect=test_module.StorageError("cannot write")
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.invitation_receive(self.request)

    async def test_oob_records_list(self):
        mock_record = mock.MagicMock(
            serialize=mock.MagicMock(return_value={"oob_id": "test"})
        )
        with (
            mock.patch.object(
                test_module.OobRecord,
                "query",
                mock.CoroutineMock(return_value=[mock_record]),
            ),
            mock.patch.object(
                test_module.web, "json_response", mock.Mock()
            ) as mock_json_response,
        ):
            await test_module.oob_records_list(self.request)
            mock_json_response.assert_called_once_with(
                {"results": [{"oob_id": "test"}]}
            )

    async def test_oob_records_list_with_filters(self):
        self.request.query = {
            "state": "initial",
            "role": "sender",
            "connection_id": "test-conn-id",
            "invi_msg_id": "test-invi-id",
        }
        with (
            mock.patch.object(
                test_module.OobRecord,
                "query",
                mock.CoroutineMock(return_value=[]),
            ) as mock_query,
            mock.patch.object(
                test_module.web, "json_response", mock.Mock()
            ) as mock_json_response,
        ):
            await test_module.oob_records_list(self.request)
            mock_query.assert_called_once()
            call_kwargs = mock_query.call_args
            tag_filter = call_kwargs[0][1]
            assert "connection_id" in tag_filter
            assert "invi_msg_id" in tag_filter
            assert "state" not in tag_filter
            mock_json_response.assert_called_once_with({"results": []})

    async def test_oob_records_list_with_pagination(self):
        self.request.query = {"limit": "10", "offset": "5"}
        with (
            mock.patch.object(
                test_module.OobRecord,
                "query",
                mock.CoroutineMock(return_value=[]),
            ) as mock_query,
            mock.patch.object(test_module.web, "json_response", mock.Mock()),
        ):
            await test_module.oob_records_list(self.request)
            mock_query.assert_called_once()
            call_kwargs = mock_query.call_args[1]
            assert call_kwargs["limit"] == 10
            assert call_kwargs["offset"] == 5

    async def test_oob_records_list_storage_error(self):
        with mock.patch.object(
            test_module.OobRecord,
            "query",
            mock.CoroutineMock(side_effect=StorageError("test error")),
        ):
            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.oob_records_list(self.request)

    async def test_register(self):
        mock_app = mock.MagicMock()
        mock_app.add_routes = mock.MagicMock()

        await test_module.register(mock_app)
        mock_app.add_routes.assert_called_once()

    async def test_post_process_routes(self):
        mock_app = mock.MagicMock(_state={"swagger_dict": {}})
        test_module.post_process_routes(mock_app)
        assert "tags" in mock_app._state["swagger_dict"]
