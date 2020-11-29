from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from aiohttp import web as aio_web

from .....connections.models.conn_record import ConnRecord
from .....core.in_memory import InMemoryProfile
from .....indy.holder import IndyHolder
from .....storage.error import StorageNotFoundError
from .....messaging.request_context import RequestContext

from .. import routes as test_module


class TestConnectionRoutes(AsyncTestCase):
    async def setUp(self):
        self.session = InMemoryProfile.test_session()
        self.context = RequestContext(self.session.profile)

    async def test_connections_list(self):
        self.context.default_endpoint = "http://1.2.3.4:8081"  # for coverage
        assert self.context.default_endpoint == "http://1.2.3.4:8081"  # for coverage
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": self.context,
        }
        mock_req.query = {
            "invitation_id": "dummy",  # exercise tag filter assignment
            "their_role": ConnRecord.Role.REQUESTER.rfc160,
        }

        STATE_COMPLETED = ConnRecord.State.COMPLETED
        STATE_INVITATION = ConnRecord.State.INVITATION
        STATE_ABANDONED = ConnRecord.State.ABANDONED
        ROLE_REQUESTER = ConnRecord.Role.REQUESTER
        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec:
            mock_conn_rec.query = async_mock.CoroutineMock()
            mock_conn_rec.Role = async_mock.MagicMock(return_value=ROLE_REQUESTER)
            mock_conn_rec.State = async_mock.MagicMock(
                COMPLETED=STATE_COMPLETED,
                INVITATION=STATE_INVITATION,
                ABANDONED=STATE_ABANDONED,
                get=async_mock.MagicMock(
                    side_effect=[
                        ConnRecord.State.ABANDONED,
                        ConnRecord.State.COMPLETED,
                        ConnRecord.State.INVITATION,
                    ]
                ),
            )
            conns = [  # in ascending order here
                async_mock.MagicMock(
                    serialize=async_mock.MagicMock(
                        return_value={
                            "state": ConnRecord.State.COMPLETED.rfc23,
                            "created_at": "1234567890",
                        }
                    )
                ),
                async_mock.MagicMock(
                    serialize=async_mock.MagicMock(
                        return_value={
                            "state": ConnRecord.State.INVITATION.rfc23,
                            "created_at": "1234567890",
                        }
                    )
                ),
                async_mock.MagicMock(
                    serialize=async_mock.MagicMock(
                        return_value={
                            "state": ConnRecord.State.ABANDONED.rfc23,
                            "created_at": "1234567890",
                        }
                    )
                ),
            ]
            mock_conn_rec.query.return_value = [conns[2], conns[0], conns[1]]  # jumbled

            with async_mock.patch.object(
                test_module.web, "json_response"
            ) as mock_response:
                await test_module.connections_list(mock_req)
                mock_response.assert_called_once_with(
                    {
                        "results": [
                            {
                                k: c.serialize.return_value[k]
                                for k in ["state", "created_at"]
                            }
                            for c in conns
                        ]
                    }  # sorted
                )

    async def test_connections_list_x(self):
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": self.context,
        }
        mock_req.query = {
            "their_role": ConnRecord.Role.REQUESTER.rfc160,
            "alias": "my connection",
            "state": ConnRecord.State.COMPLETED.rfc23,
        }

        STATE_COMPLETED = ConnRecord.State.COMPLETED
        ROLE_REQUESTER = ConnRecord.Role.REQUESTER
        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec:
            mock_conn_rec.Role = async_mock.MagicMock(return_value=ROLE_REQUESTER)
            mock_conn_rec.State = async_mock.MagicMock(
                COMPLETED=STATE_COMPLETED,
                get=async_mock.MagicMock(return_value=ConnRecord.State.COMPLETED),
            )
            mock_conn_rec.query = async_mock.CoroutineMock(
                side_effect=test_module.StorageError()
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.connections_list(mock_req)

    async def test_connections_retrieve(self):
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": self.context,
        }
        mock_req.match_info = {"conn_id": "dummy"}
        mock_conn_rec = async_mock.MagicMock()
        mock_conn_rec.serialize = async_mock.MagicMock(return_value={"hello": "world"})

        with async_mock.patch.object(
            test_module.ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_conn_rec_retrieve_by_id.return_value = mock_conn_rec

            await test_module.connections_retrieve(mock_req)
            mock_response.assert_called_once_with({"hello": "world"})

    async def test_connections_retrieve_not_found(self):
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": self.context,
        }
        mock_req.match_info = {"conn_id": "dummy"}

        with async_mock.patch.object(
            test_module.ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id:
            mock_conn_rec_retrieve_by_id.side_effect = StorageNotFoundError()

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.connections_retrieve(mock_req)

    async def test_connections_retrieve_x(self):
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": self.context,
        }
        mock_req.match_info = {"conn_id": "dummy"}
        mock_conn_rec = async_mock.MagicMock()
        mock_conn_rec.serialize = async_mock.MagicMock(
            side_effect=test_module.BaseModelError()
        )

        with async_mock.patch.object(
            test_module.ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id:
            mock_conn_rec_retrieve_by_id.return_value = mock_conn_rec

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.connections_retrieve(mock_req)

    async def test_connections_create_invitation(self):
        mock_req = async_mock.MagicMock()
        self.context._context.update_settings({"public_invites": True})
        mock_req.app = {
            "request_context": self.context,
        }
        mock_req.json = async_mock.CoroutineMock()
        mock_req.query = {
            "auto_accept": "true",
            "alias": "alias",
            "public": "true",
            "multi_use": "true",
        }

        with async_mock.patch.object(
            test_module, "ConnectionManager", autospec=True
        ) as mock_conn_mgr, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:

            mock_conn_mgr.return_value.create_invitation = async_mock.CoroutineMock(
                return_value=(
                    async_mock.MagicMock(  # connection record
                        connection_id="dummy", alias="conn-alias"
                    ),
                    async_mock.MagicMock(  # invitation
                        serialize=async_mock.MagicMock(return_value={"a": "value"}),
                        to_url=async_mock.MagicMock(return_value="http://endpoint.ca"),
                    ),
                )
            )

            await test_module.connections_create_invitation(mock_req)
            mock_response.assert_called_once_with(
                {
                    "connection_id": "dummy",
                    "invitation": {"a": "value"},
                    "invitation_url": "http://endpoint.ca",
                    "alias": "conn-alias",
                }
            )

    async def test_connections_create_invitation_x(self):
        mock_req = async_mock.MagicMock()
        self.context._context.update_settings({"public_invites": True})
        mock_req.app = {
            "request_context": self.context,
        }
        mock_req.json = async_mock.CoroutineMock()
        mock_req.query = {
            "auto_accept": "true",
            "alias": "alias",
            "public": "true",
            "multi_use": "true",
        }

        with async_mock.patch.object(
            test_module, "ConnectionManager", autospec=True
        ) as mock_conn_mgr:
            mock_conn_mgr.return_value.create_invitation = async_mock.CoroutineMock(
                side_effect=test_module.ConnectionManagerError()
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.connections_create_invitation(mock_req)

    async def test_connections_create_invitation_public_forbidden(self):
        mock_req = async_mock.MagicMock()
        self.context._context.update_settings({"public_invites": False})
        mock_req.app = {
            "request_context": self.context,
        }
        mock_req.json = async_mock.CoroutineMock()
        mock_req.query = {
            "auto_accept": "true",
            "alias": "alias",
            "public": "true",
            "multi_use": "true",
        }

        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.connections_create_invitation(mock_req)

    async def test_connections_receive_invitation(self):
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": self.context,
        }
        mock_req.json = async_mock.CoroutineMock()
        mock_req.query = {
            "auto_accept": "true",
            "alias": "alias",
        }

        mock_conn_rec = async_mock.MagicMock()
        mock_conn_rec.serialize = async_mock.MagicMock()

        with async_mock.patch.object(
            test_module.ConnectionInvitation, "deserialize", autospec=True
        ) as mock_inv_deser, async_mock.patch.object(
            test_module, "ConnectionManager", autospec=True
        ) as mock_conn_mgr, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_conn_mgr.return_value.receive_invitation = async_mock.CoroutineMock(
                return_value=mock_conn_rec
            )

            await test_module.connections_receive_invitation(mock_req)
            mock_response.assert_called_once_with(mock_conn_rec.serialize.return_value)

    async def test_connections_receive_invitation_bad(self):
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": self.context,
        }
        mock_req.json = async_mock.CoroutineMock()
        mock_req.query = {
            "auto_accept": "true",
            "alias": "alias",
        }

        mock_conn_rec = async_mock.MagicMock()
        mock_conn_rec.serialize = async_mock.MagicMock()

        with async_mock.patch.object(
            test_module.ConnectionInvitation, "deserialize", autospec=True
        ) as mock_inv_deser, async_mock.patch.object(
            test_module, "ConnectionManager", autospec=True
        ) as mock_conn_mgr:
            mock_inv_deser.side_effect = test_module.BaseModelError()

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.connections_receive_invitation(mock_req)

    async def test_connections_receive_invitation_forbidden(self):
        self.context._context.update_settings({"admin.no_receive_invites": True})
        mock_req = async_mock.MagicMock()

        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.connections_receive_invitation(mock_req)

    async def test_connections_accept_invitation(self):
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": self.context,
            "outbound_message_router": async_mock.CoroutineMock(),
        }
        mock_req.match_info = {"conn_id": "dummy"}
        mock_req.query = {
            "my_label": "label",
            "my_endpoint": "http://endpoint.ca",
        }

        mock_conn_rec = async_mock.MagicMock()
        mock_conn_rec.serialize = async_mock.MagicMock()

        with async_mock.patch.object(
            test_module.ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id, async_mock.patch.object(
            test_module, "ConnectionManager", autospec=True
        ) as mock_conn_mgr, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:

            mock_conn_rec_retrieve_by_id.return_value = mock_conn_rec
            mock_conn_mgr.return_value.create_request = async_mock.CoroutineMock()

            await test_module.connections_accept_invitation(mock_req)
            mock_response.assert_called_once_with(mock_conn_rec.serialize.return_value)

    async def test_connections_accept_invitation_not_found(self):
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": self.context,
            "outbound_message_router": async_mock.CoroutineMock(),
        }
        mock_req.match_info = {"conn_id": "dummy"}

        with async_mock.patch.object(
            test_module.ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id:
            mock_conn_rec_retrieve_by_id.side_effect = StorageNotFoundError()

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.connections_accept_invitation(mock_req)

    async def test_connections_accept_invitation_x(self):
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": self.context,
            "outbound_message_router": async_mock.CoroutineMock(),
        }
        mock_req.match_info = {"conn_id": "dummy"}

        with async_mock.patch.object(
            test_module.ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id, async_mock.patch.object(
            test_module, "ConnectionManager", autospec=True
        ) as mock_conn_mgr:
            mock_conn_mgr.return_value.create_request = async_mock.CoroutineMock(
                side_effect=test_module.ConnectionManagerError()
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.connections_accept_invitation(mock_req)

    async def test_connections_accept_request(self):
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": self.context,
            "outbound_message_router": async_mock.CoroutineMock(),
        }
        mock_req.match_info = {"conn_id": "dummy"}
        mock_req.query = {
            "my_endpoint": "http://endpoint.ca",
        }

        mock_conn_rec = async_mock.MagicMock()
        mock_conn_rec.serialize = async_mock.MagicMock()

        with async_mock.patch.object(
            test_module.ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id, async_mock.patch.object(
            test_module, "ConnectionManager", autospec=True
        ) as mock_conn_mgr, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_conn_rec_retrieve_by_id.return_value = mock_conn_rec
            mock_conn_mgr.return_value.create_response = async_mock.CoroutineMock()

            await test_module.connections_accept_request(mock_req)
            mock_response.assert_called_once_with(mock_conn_rec.serialize.return_value)

    async def test_connections_accept_request_not_found(self):
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": self.context,
            "outbound_message_router": async_mock.CoroutineMock(),
        }
        mock_req.match_info = {"conn_id": "dummy"}

        with async_mock.patch.object(
            test_module.ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id:
            mock_conn_rec_retrieve_by_id.side_effect = StorageNotFoundError()

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.connections_accept_request(mock_req)

    async def test_connections_accept_request_x(self):
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": self.context,
            "outbound_message_router": async_mock.CoroutineMock(),
        }
        mock_req.match_info = {"conn_id": "dummy"}

        with async_mock.patch.object(
            test_module.ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id, async_mock.patch.object(
            test_module, "ConnectionManager", autospec=True
        ) as mock_conn_mgr, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_conn_mgr.return_value.create_response = async_mock.CoroutineMock(
                side_effect=test_module.ConnectionManagerError()
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.connections_accept_request(mock_req)

    async def test_connections_establish_inbound(self):
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": self.context,
            "outbound_message_router": async_mock.CoroutineMock(),
        }
        mock_req.match_info = {"conn_id": "dummy", "ref_id": "ref"}
        mock_req.query = {
            "my_endpoint": "http://endpoint.ca",
        }
        mock_conn_rec = async_mock.MagicMock()

        with async_mock.patch.object(
            test_module.ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id, async_mock.patch.object(
            test_module, "ConnectionManager", autospec=True
        ) as mock_conn_mgr, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_conn_rec_retrieve_by_id.return_value = mock_conn_rec
            mock_conn_mgr.return_value.establish_inbound = async_mock.CoroutineMock()

            await test_module.connections_establish_inbound(mock_req)
            mock_response.assert_called_once_with({})

    async def test_connections_establish_inbound_not_found(self):
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": self.context,
            "outbound_message_router": async_mock.CoroutineMock(),
        }
        mock_req.match_info = {"conn_id": "dummy", "ref_id": "ref"}

        with async_mock.patch.object(
            test_module.ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id:
            mock_conn_rec_retrieve_by_id.side_effect = StorageNotFoundError()

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.connections_establish_inbound(mock_req)

    async def test_connections_establish_inbound_x(self):
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": self.context,
            "outbound_message_router": async_mock.CoroutineMock(),
        }
        mock_req.match_info = {"conn_id": "dummy", "ref_id": "ref"}
        mock_req.query = {
            "my_endpoint": "http://endpoint.ca",
        }
        mock_conn_rec = async_mock.MagicMock()

        with async_mock.patch.object(
            test_module.ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id, async_mock.patch.object(
            test_module, "ConnectionManager", autospec=True
        ) as mock_conn_mgr:
            mock_conn_rec_retrieve_by_id.return_value = mock_conn_rec
            mock_conn_mgr.return_value.establish_inbound = async_mock.CoroutineMock(
                side_effect=test_module.ConnectionManagerError()
            )
            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.connections_establish_inbound(mock_req)

    async def test_connections_remove(self):
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": self.context,
        }
        mock_req.match_info = {"conn_id": "dummy"}
        mock_conn_rec = async_mock.MagicMock()
        mock_conn_rec.delete_record = async_mock.CoroutineMock()

        with async_mock.patch.object(
            test_module.ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_conn_rec_retrieve_by_id.return_value = mock_conn_rec

            await test_module.connections_remove(mock_req)
            mock_response.assert_called_once_with({})

    async def test_connections_remove_not_found(self):
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": self.context,
        }
        mock_req.match_info = {"conn_id": "dummy"}

        mock_conn_rec = async_mock.MagicMock()

        with async_mock.patch.object(
            test_module.ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id:
            mock_conn_rec_retrieve_by_id.side_effect = StorageNotFoundError()

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.connections_remove(mock_req)

    async def test_connections_remove_x(self):
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": self.context,
        }
        mock_req.match_info = {"conn_id": "dummy"}
        mock_conn_rec = async_mock.MagicMock(
            delete_record=async_mock.CoroutineMock(
                side_effect=test_module.StorageError()
            )
        )

        with async_mock.patch.object(
            test_module.ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id:
            mock_conn_rec_retrieve_by_id.return_value = mock_conn_rec

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.connections_remove(mock_req)

    async def test_connections_create_static(self):
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": self.context,
        }
        mock_req.json = async_mock.CoroutineMock(
            return_value={
                "my_seed": "my_seed",
                "my_did": "my_did",
                "their_seed": "their_seed",
                "their_did": "their_did",
                "their_verkey": "their_verkey",
                "their_endpoint": "their_endpoint",
                "their_role": "their_role",
                "alias": "alias",
            }
        )
        mock_req.query = {
            "auto_accept": "true",
            "alias": "alias",
        }
        mock_req.match_info = {"conn_id": "dummy"}

        mock_conn_rec = async_mock.MagicMock()
        mock_conn_rec.serialize = async_mock.MagicMock()
        mock_my_info = async_mock.MagicMock()
        mock_my_info.did = "my_did"
        mock_my_info.verkey = "my_verkey"
        mock_their_info = async_mock.MagicMock()
        mock_their_info.did = "their_did"
        mock_their_info.verkey = "their_verkey"

        with async_mock.patch.object(
            test_module, "ConnectionManager", autospec=True
        ) as mock_conn_mgr, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_conn_mgr.return_value.create_static_connection = (
                async_mock.CoroutineMock(
                    return_value=(mock_my_info, mock_their_info, mock_conn_rec)
                )
            )

            await test_module.connections_create_static(mock_req)
            mock_response.assert_called_once_with(
                {
                    "my_did": mock_my_info.did,
                    "my_verkey": mock_my_info.verkey,
                    "their_did": mock_their_info.did,
                    "their_verkey": mock_their_info.verkey,
                    "my_endpoint": self.context.settings.get("default_endpoint"),
                    "record": mock_conn_rec.serialize.return_value,
                }
            )

    async def test_connections_create_static_x(self):
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": self.context,
        }
        mock_req.json = async_mock.CoroutineMock(
            return_value={
                "my_seed": "my_seed",
                "my_did": "my_did",
                "their_seed": "their_seed",
                "their_did": "their_did",
                "their_verkey": "their_verkey",
                "their_endpoint": "their_endpoint",
                "their_role": "their_role",
                "alias": "alias",
            }
        )
        mock_req.query = {
            "auto_accept": "true",
            "alias": "alias",
        }
        mock_req.match_info = {"conn_id": "dummy"}

        mock_conn_rec = async_mock.MagicMock()
        mock_conn_rec.serialize = async_mock.MagicMock()
        mock_my_info = async_mock.MagicMock()
        mock_my_info.did = "my_did"
        mock_my_info.verkey = "my_verkey"
        mock_their_info = async_mock.MagicMock()
        mock_their_info.did = "their_did"
        mock_their_info.verkey = "their_verkey"

        with async_mock.patch.object(
            test_module, "ConnectionManager", autospec=True
        ) as mock_conn_mgr:
            mock_conn_mgr.return_value.create_static_connection = (
                async_mock.CoroutineMock(side_effect=test_module.WalletError())
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.connections_create_static(mock_req)

    async def test_register(self):
        mock_app = async_mock.MagicMock()
        mock_app.add_routes = async_mock.MagicMock()

        await test_module.register(mock_app)
        mock_app.add_routes.assert_called_once()

    async def test_post_process_routes(self):
        mock_app = async_mock.MagicMock(_state={"swagger_dict": {}})
        test_module.post_process_routes(mock_app)
        assert "tags" in mock_app._state["swagger_dict"]
