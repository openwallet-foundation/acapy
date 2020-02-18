from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from aiohttp import web as aio_web

from ....config.injection_context import InjectionContext
from ....connections.models.connection_record import ConnectionRecord
from ....storage.error import StorageNotFoundError
from ....holder.base import BaseHolder
from ....messaging.request_context import RequestContext
from .. import routes as test_module


class TestConnectionRoutes(AsyncTestCase):
    async def test_connections_list(self):
        context = RequestContext(base_context=InjectionContext(enforce_typing=False))
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": context,
        }
        mock_req.query = {
            "invitation_id": "dummy",
            "initiator": ConnectionRecord.INITIATOR_SELF,
        }

        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_conn_rec:
            mock_conn_rec.STATE_INVITATION = ConnectionRecord.STATE_INVITATION
            mock_conn_rec.STATE_INACTIVE = ConnectionRecord.STATE_INACTIVE
            mock_conn_rec.query = async_mock.CoroutineMock()
            conns = [  # in order here
                async_mock.MagicMock(
                    serialize=async_mock.MagicMock(
                        return_value={
                            "state": ConnectionRecord.STATE_ACTIVE,
                            "created_at": "1234567890",
                        }
                    )
                ),
                async_mock.MagicMock(
                    serialize=async_mock.MagicMock(
                        return_value={
                            "state": ConnectionRecord.STATE_INVITATION,
                            "created_at": "1234567890",
                        }
                    )
                ),
                async_mock.MagicMock(
                    serialize=async_mock.MagicMock(
                        return_value={
                            "state": ConnectionRecord.STATE_INACTIVE,
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

    async def test_connections_retrieve(self):
        context = RequestContext(base_context=InjectionContext(enforce_typing=False))
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": context,
        }
        mock_req.match_info = {"id": "dummy"}

        mock_conn_rec = async_mock.MagicMock()
        mock_conn_rec.serialize = async_mock.MagicMock(return_value={"hello": "world"})

        with async_mock.patch.object(
            test_module.ConnectionRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:

            mock_conn_rec_retrieve_by_id.return_value = mock_conn_rec

            await test_module.connections_retrieve(mock_req)
            mock_response.assert_called_once_with({"hello": "world"})

    async def test_connections_retrieve_not_found(self):
        context = RequestContext(base_context=InjectionContext(enforce_typing=False))
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": context,
        }
        mock_req.match_info = {"id": "dummy"}

        with async_mock.patch.object(
            test_module.ConnectionRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id:
            mock_conn_rec_retrieve_by_id.side_effect = StorageNotFoundError()

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.connections_retrieve(mock_req)

    async def test_connections_create_invitation(self):
        context = RequestContext(base_context=InjectionContext(enforce_typing=False))
        mock_req = async_mock.MagicMock()
        context.update_settings({"public_invites": True})
        mock_req.app = {
            "request_context": context,
        }
        mock_req.query = {
            "accept": "auto",
            "alias": "alias",
            "public": 1,
            "multi_use": 1,
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

    async def test_connections_create_invitation_public_forbidden(self):
        context = RequestContext(base_context=InjectionContext(enforce_typing=False))
        mock_req = async_mock.MagicMock()
        context.update_settings({"public_invites": False})
        mock_req.app = {
            "request_context": context,
        }
        mock_req.query = {
            "accept": "auto",
            "alias": "alias",
            "public": 1,
            "multi_use": 1,
        }

        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.connections_create_invitation(mock_req)

    async def test_connections_receive_invitation(self):
        context = RequestContext(base_context=InjectionContext(enforce_typing=False))
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": context,
        }
        mock_req.json = async_mock.CoroutineMock()
        mock_req.query = {
            "accept": "auto",
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

    async def test_connections_receive_invitation_forbidden(self):
        context = RequestContext(base_context=InjectionContext(enforce_typing=False))
        context.update_settings({"admin.no_receive_invites": True})
        mock_req = async_mock.MagicMock()

        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.connections_receive_invitation(mock_req)

    async def test_connections_accept_invitation(self):
        context = RequestContext(base_context=InjectionContext(enforce_typing=False))
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": context,
            "outbound_message_router": async_mock.CoroutineMock(),
        }
        mock_req.match_info = {"id": "dummy"}
        mock_req.query = {
            "my_label": "label",
            "my_endpoint": "http://endpoint.ca",
        }

        mock_conn_rec = async_mock.MagicMock()
        mock_conn_rec.serialize = async_mock.MagicMock()

        with async_mock.patch.object(
            test_module.ConnectionRecord, "retrieve_by_id", async_mock.CoroutineMock()
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
        context = RequestContext(base_context=InjectionContext(enforce_typing=False))
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": context,
            "outbound_message_router": async_mock.CoroutineMock(),
        }
        mock_req.match_info = {"id": "dummy"}

        with async_mock.patch.object(
            test_module.ConnectionRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id:
            mock_conn_rec_retrieve_by_id.side_effect = StorageNotFoundError()

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.connections_accept_invitation(mock_req)

    async def test_connections_accept_request(self):
        context = RequestContext(base_context=InjectionContext(enforce_typing=False))
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": context,
            "outbound_message_router": async_mock.CoroutineMock(),
        }
        mock_req.match_info = {"id": "dummy"}
        mock_req.query = {
            "my_endpoint": "http://endpoint.ca",
        }

        mock_conn_rec = async_mock.MagicMock()
        mock_conn_rec.serialize = async_mock.MagicMock()

        with async_mock.patch.object(
            test_module.ConnectionRecord, "retrieve_by_id", async_mock.CoroutineMock()
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
        context = RequestContext(base_context=InjectionContext(enforce_typing=False))
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": context,
            "outbound_message_router": async_mock.CoroutineMock(),
        }
        mock_req.match_info = {"id": "dummy"}

        with async_mock.patch.object(
            test_module.ConnectionRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id:
            mock_conn_rec_retrieve_by_id.side_effect = StorageNotFoundError()

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.connections_accept_request(mock_req)

    async def test_connections_establish_inbound(self):
        context = RequestContext(base_context=InjectionContext(enforce_typing=False))
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": context,
            "outbound_message_router": async_mock.CoroutineMock(),
        }
        mock_req.match_info = {"id": "dummy", "ref_id": "ref"}
        mock_req.query = {
            "my_endpoint": "http://endpoint.ca",
        }

        mock_conn_rec = async_mock.MagicMock()

        with async_mock.patch.object(
            test_module.ConnectionRecord, "retrieve_by_id", async_mock.CoroutineMock()
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
        context = RequestContext(base_context=InjectionContext(enforce_typing=False))
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": context,
            "outbound_message_router": async_mock.CoroutineMock(),
        }
        mock_req.match_info = {"id": "dummy", "ref_id": "ref"}

        with async_mock.patch.object(
            test_module.ConnectionRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id:
            mock_conn_rec_retrieve_by_id.side_effect = StorageNotFoundError()

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.connections_establish_inbound(mock_req)

    async def test_connections_remove(self):
        context = RequestContext(base_context=InjectionContext(enforce_typing=False))
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": context,
        }
        mock_req.match_info = {"id": "dummy"}

        mock_conn_rec = async_mock.MagicMock()
        mock_conn_rec.delete_record = async_mock.CoroutineMock()

        with async_mock.patch.object(
            test_module.ConnectionRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_conn_rec_retrieve_by_id.return_value = mock_conn_rec

            await test_module.connections_remove(mock_req)
            mock_response.assert_called_once_with({})

    async def test_connections_remove_not_found(self):
        context = RequestContext(base_context=InjectionContext(enforce_typing=False))
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": context,
        }
        mock_req.match_info = {"id": "dummy"}

        mock_conn_rec = async_mock.MagicMock()

        with async_mock.patch.object(
            test_module.ConnectionRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id:
            mock_conn_rec_retrieve_by_id.side_effect = StorageNotFoundError()

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.connections_remove(mock_req)

    async def test_connections_create_static(self):
        context = RequestContext(base_context=InjectionContext(enforce_typing=False))
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": context,
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
            "accept": "auto",
            "alias": "alias",
        }
        mock_req.match_info = {"id": "dummy"}

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

            mock_conn_mgr.return_value.create_static_connection = async_mock.CoroutineMock(
                return_value=(mock_my_info, mock_their_info, mock_conn_rec)
            )

            await test_module.connections_create_static(mock_req)
            mock_response.assert_called_once_with({
                "my_did": mock_my_info.did,
                "my_verkey": mock_my_info.verkey,
                "their_did": mock_their_info.did,
                "their_verkey": mock_their_info.verkey,
                "my_endpoint": context.settings.get("default_endpoint"),
                "record": mock_conn_rec.serialize.return_value
            })

    async def test_register(self):
        mock_app = async_mock.MagicMock()
        mock_app.add_routes = async_mock.MagicMock()

        await test_module.register(mock_app)
        mock_app.add_routes.assert_called_once()

