from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from aiohttp import web as aio_web

from aries_cloudagent.config.injection_context import InjectionContext
from aries_cloudagent.connections.models.connection_record import ConnectionRecord
from aries_cloudagent.connections.models.conn23rec import Conn23Record
from aries_cloudagent.storage.error import StorageNotFoundError
from aries_cloudagent.holder.base import BaseHolder
from aries_cloudagent.messaging.request_context import RequestContext

from .. import routes as test_module


class TestDIDExchangeConnRoutes(AsyncTestCase):
    async def test_connections_list_rfc160(self):
        context = RequestContext(base_context=InjectionContext(enforce_typing=False))
        context.default_endpoint = "http://1.2.3.4:8081"  # for coverage
        assert context.default_endpoint == "http://1.2.3.4:8081"  # for coverage
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": context,
        }
        mock_req.query = {
            "invitation_id": "dummy",
            "their_role": Conn23Record.Role.REQUESTER.rfc160,
        }

        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_conn160_rec, async_mock.patch.object(
            test_module, "Conn23Record", autospec=True
        ) as mock_conn23_rec:
            mock_conn160_rec.STATE_ACTIVE = ConnectionRecord.STATE_ACTIVE
            mock_conn160_rec.STATE_INVITATION = ConnectionRecord.STATE_INVITATION
            mock_conn160_rec.STATE_INACTIVE = ConnectionRecord.STATE_INACTIVE
            mock_conn160_rec.query = async_mock.CoroutineMock()
            mock_conn23_rec.query = async_mock.CoroutineMock(
                return_value=[]
            )
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
            mock_conn160_rec.query.return_value = [
                conns[2], conns[0], conns[1]  # jumbled
            ]

            with async_mock.patch.object(
                test_module.web, "json_response"
            ) as mock_response:
                await test_module.connections_list(mock_req)
                mock_response.assert_called_once_with(
                    {
                        "rfc160_connections": [
                            {
                                k: c.serialize.return_value[k]
                                for k in ["state", "created_at"]
                            }
                            for c in conns
                        ],
                        "rfc23_connections": [
                        ]
                    }  # sorted
                )

    async def test_connections_list_rfc23(self):
        context = RequestContext(base_context=InjectionContext(enforce_typing=False))
        context.default_endpoint = "http://1.2.3.4:8081"  # for coverage
        assert context.default_endpoint == "http://1.2.3.4:8081"  # for coverage
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": context,
        }
        mock_req.query = {
            "invitation_id": "dummy",
            "their_role": Conn23Record.Role.REQUESTER.rfc23,
        }

        with async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_conn160_rec, async_mock.patch.object(
            test_module, "Conn23Record", autospec=True
        ) as mock_conn23_rec:
            mock_conn23_rec.STATE_COMPLETED = Conn23Record.STATE_COMPLETED
            mock_conn23_rec.STATE_INVITATION = Conn23Record.STATE_INVITATION
            mock_conn23_rec.STATE_ABANDONED = Conn23Record.STATE_ABANDONED
            mock_conn23_rec.query = async_mock.CoroutineMock()
            mock_conn160_rec.query = async_mock.CoroutineMock(
                return_value=[]
            )
            conns = [  # in order here
                async_mock.MagicMock(
                    serialize=async_mock.MagicMock(
                        return_value={
                            "state": Conn23Record.STATE_COMPLETED,
                            "created_at": "1234567890",
                        }
                    )
                ),
                async_mock.MagicMock(
                    serialize=async_mock.MagicMock(
                        return_value={
                            "state": Conn23Record.STATE_INVITATION,
                            "created_at": "1234567890",
                        }
                    )
                ),
                async_mock.MagicMock(
                    serialize=async_mock.MagicMock(
                        return_value={
                            "state": Conn23Record.STATE_ABANDONED,
                            "created_at": "1234567890",
                        }
                    )
                ),
            ]
            mock_conn23_rec.query.return_value = [
                conns[2], conns[0], conns[1]  # jumbled
                ]

            with async_mock.patch.object(
                test_module.web, "json_response"
            ) as mock_response:
                await test_module.connections_list(mock_req)
                mock_response.assert_called_once_with(
                    {
                        "rfc23_connections": [
                            {
                                k: c.serialize.return_value[k]
                                for k in ["state", "created_at"]
                            }
                            for c in conns
                        ],
                        "rfc160_connections": [
                        ]
                    }  # sorted
                )

    async def test_connections_list_x(self):
        context = RequestContext(base_context=InjectionContext(enforce_typing=False))
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": context,
        }
        mock_req.query = {
            "invitation_id": "dummy",
            "their_role": Conn23Record.Role.REQUESTER.rfc23,
        }

        with async_mock.patch.object(
            test_module, "Conn23Record", autospec=True
        ) as mock_conn23_rec, async_mock.patch.object(
            test_module, "ConnectionRecord", autospec=True
        ) as mock_conn160_rec:
            mock_conn23_rec.query = async_mock.CoroutineMock(
                side_effect=test_module.StorageError()
            )
            mock_conn160_rec.query = async_mock.CoroutineMock(
                side_effect=test_module.StorageError()
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.connections_list(mock_req)

    async def test_connections_retrieve(self):
        context = RequestContext(base_context=InjectionContext(enforce_typing=False))
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": context,
        }
        mock_req.match_info = {"conn_id": "dummy"}
        mock_conn160_rec = async_mock.MagicMock()
        mock_conn160_rec.serialize = async_mock.MagicMock(
            return_value={"hello": "world"}
        )

        with async_mock.patch.object(
            test_module.Conn23Record, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn23_rec_retrieve_by_id, async_mock.patch.object(
            test_module.ConnectionRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn160_rec_retrieve_by_id, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_conn23_rec_retrieve_by_id.side_effect = StorageNotFoundError()
            mock_conn160_rec_retrieve_by_id.return_value = mock_conn160_rec

            await test_module.connections_retrieve(mock_req)
            mock_response.assert_called_once_with(
                {
                    "rfc160_connection": {"hello": "world"}
                }
            )

    async def test_connections_retrieve_not_found(self):
        context = RequestContext(base_context=InjectionContext(enforce_typing=False))
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": context,
        }
        mock_req.match_info = {"conn_id": "dummy"}

        with async_mock.patch.object(
            test_module.Conn23Record, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn160_rec_retrieve_by_id, async_mock.patch.object(
            test_module.ConnectionRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn23_rec_retrieve_by_id:
            mock_conn160_rec_retrieve_by_id.side_effect = StorageNotFoundError()
            mock_conn23_rec_retrieve_by_id.side_effect = StorageNotFoundError()

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.connections_retrieve(mock_req)

    async def test_connections_retrieve_23x(self):
        context = RequestContext(base_context=InjectionContext(enforce_typing=False))
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": context,
        }
        mock_req.match_info = {"conn_id": "dummy"}
        mock_conn_rec = async_mock.MagicMock()
        mock_conn_rec.serialize = async_mock.MagicMock(
            side_effect=test_module.BaseModelError()
        )

        with async_mock.patch.object(
            test_module.Conn23Record, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id:
            mock_conn_rec_retrieve_by_id.return_value = mock_conn_rec

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.connections_retrieve(mock_req)

    async def test_connections_retrieve_160x(self):
        context = RequestContext(base_context=InjectionContext(enforce_typing=False))
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": context,
        }
        mock_req.match_info = {"conn_id": "dummy"}
        mock_conn160_rec = async_mock.MagicMock()
        mock_conn160_rec.serialize = async_mock.MagicMock(
            side_effect=test_module.BaseModelError()
        )

        with async_mock.patch.object(
            test_module.Conn23Record, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id:
            mock_conn_rec_retrieve_by_id.side_effect = StorageNotFoundError()

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.connections_retrieve(mock_req)

    async def test_connections_receive_invitation(self):
        context = RequestContext(base_context=InjectionContext(enforce_typing=False))
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": context,
        }
        mock_req.json = async_mock.CoroutineMock()
        mock_req.query = {
            "auto_accept": "true",
            "alias": "alias",
        }

        mock_conn_rec = async_mock.MagicMock()
        mock_conn_rec.serialize = async_mock.MagicMock()

        with async_mock.patch.object(
            test_module.OOBInvitation, "deserialize", autospec=True
        ) as mock_inv_deser, async_mock.patch.object(
            test_module, "Conn23Manager", autospec=True
        ) as mock_conn_mgr, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_conn_mgr.return_value.receive_invitation = async_mock.CoroutineMock(
                return_value=mock_conn_rec
            )

            await test_module.connections_receive_invitation(mock_req)
            mock_response.assert_called_once_with(mock_conn_rec.serialize.return_value)

    async def test_connections_receive_invitation_bad(self):
        context = RequestContext(base_context=InjectionContext(enforce_typing=False))
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": context,
        }
        mock_req.json = async_mock.CoroutineMock()
        mock_req.query = {
            "auto_accept": "true",
            "alias": "alias",
        }

        mock_conn_rec = async_mock.MagicMock()
        mock_conn_rec.serialize = async_mock.MagicMock()

        with async_mock.patch.object(
            test_module.OOBInvitation, "deserialize", autospec=True
        ) as mock_inv_deser, async_mock.patch.object(
            test_module, "Conn23Manager", autospec=True
        ) as mock_conn_mgr:
            mock_inv_deser.side_effect = test_module.BaseModelError()

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.connections_receive_invitation(mock_req)

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
        mock_req.match_info = {"conn_id": "dummy"}
        mock_req.query = {
            "my_label": "label",
            "my_endpoint": "http://endpoint.ca",
        }

        mock_conn_rec = async_mock.MagicMock(
            save=async_mock.CoroutineMock()
        )
        mock_conn_rec.serialize = async_mock.MagicMock()

        with async_mock.patch.object(
            test_module, "Conn23Record", autospec=True
        ) as mock_conn23_rec, async_mock.patch.object(
            test_module, "Conn23Manager", autospec=True
        ) as mock_conn_mgr, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:

            mock_conn23_rec.retrieve_by_id.return_value = mock_conn_rec
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
        mock_req.match_info = {"conn_id": "dummy"}

        with async_mock.patch.object(
            test_module.Conn23Record, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id:
            mock_conn_rec_retrieve_by_id.side_effect = StorageNotFoundError()

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.connections_accept_invitation(mock_req)

    async def test_connections_accept_invitation_x(self):
        context = RequestContext(base_context=InjectionContext(enforce_typing=False))
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": context,
            "outbound_message_router": async_mock.CoroutineMock(),
        }
        mock_req.match_info = {"conn_id": "dummy"}

        with async_mock.patch.object(
            test_module.Conn23Record, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id, async_mock.patch.object(
            test_module, "Conn23Manager", autospec=True
        ) as mock_conn_mgr:
            mock_conn_mgr.return_value.create_request = async_mock.CoroutineMock(
                side_effect=test_module.Conn23ManagerError()
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.connections_accept_invitation(mock_req)

    async def test_connections_accept_request(self):
        context = RequestContext(base_context=InjectionContext(enforce_typing=False))
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": context,
            "outbound_message_router": async_mock.CoroutineMock(),
        }
        mock_req.match_info = {"conn_id": "dummy"}
        mock_req.query = {
            "my_endpoint": "http://endpoint.ca",
        }

        mock_conn_rec = async_mock.MagicMock()
        mock_conn_rec.serialize = async_mock.MagicMock()

        with async_mock.patch.object(
            test_module.Conn23Record, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id, async_mock.patch.object(
            test_module, "Conn23Manager", autospec=True
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
        mock_req.match_info = {"conn_id": "dummy"}

        with async_mock.patch.object(
            test_module.Conn23Record, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id:
            mock_conn_rec_retrieve_by_id.side_effect = StorageNotFoundError()

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.connections_accept_request(mock_req)

    async def test_connections_accept_request_x(self):
        context = RequestContext(base_context=InjectionContext(enforce_typing=False))
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": context,
            "outbound_message_router": async_mock.CoroutineMock(),
        }
        mock_req.match_info = {"conn_id": "dummy"}

        with async_mock.patch.object(
            test_module.Conn23Record, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id, async_mock.patch.object(
            test_module, "Conn23Manager", autospec=True
        ) as mock_conn_mgr, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_conn_mgr.return_value.create_response = async_mock.CoroutineMock(
                side_effect=test_module.Conn23ManagerError()
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.connections_accept_request(mock_req)

    async def test_connections_establish_inbound(self):
        context = RequestContext(base_context=InjectionContext(enforce_typing=False))
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": context,
            "outbound_message_router": async_mock.CoroutineMock(),
        }
        mock_req.match_info = {"conn_id": "dummy", "ref_id": "ref"}
        mock_req.query = {
            "my_endpoint": "http://endpoint.ca",
        }
        mock_conn_rec = async_mock.MagicMock()

        with async_mock.patch.object(
            test_module.Conn23Record, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id, async_mock.patch.object(
            test_module, "Conn23Manager", autospec=True
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
        mock_req.match_info = {"conn_id": "dummy", "ref_id": "ref"}

        with async_mock.patch.object(
            test_module.Conn23Record, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id:
            mock_conn_rec_retrieve_by_id.side_effect = StorageNotFoundError()

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.connections_establish_inbound(mock_req)

    async def test_connections_establish_inbound_x(self):
        context = RequestContext(base_context=InjectionContext(enforce_typing=False))
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": context,
            "outbound_message_router": async_mock.CoroutineMock(),
        }
        mock_req.match_info = {"conn_id": "dummy", "ref_id": "ref"}
        mock_req.query = {
            "my_endpoint": "http://endpoint.ca",
        }
        mock_conn_rec = async_mock.MagicMock()

        with async_mock.patch.object(
            test_module.Conn23Record, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id, async_mock.patch.object(
            test_module, "Conn23Manager", autospec=True
        ) as mock_conn_mgr:
            mock_conn_rec_retrieve_by_id.return_value = mock_conn_rec
            mock_conn_mgr.return_value.establish_inbound = async_mock.CoroutineMock(
                side_effect=test_module.Conn23ManagerError()
            )
            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.connections_establish_inbound(mock_req)

    async def test_connections_remove(self):
        context = RequestContext(base_context=InjectionContext(enforce_typing=False))
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": context,
        }
        mock_req.match_info = {"conn_id": "dummy"}
        mock_conn_rec = async_mock.MagicMock()
        mock_conn_rec.delete_record = async_mock.CoroutineMock()

        with async_mock.patch.object(
            test_module.Conn23Record, "retrieve_by_id", async_mock.CoroutineMock()
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
        mock_req.match_info = {"conn_id": "dummy"}

        mock_conn_rec = async_mock.MagicMock()

        with async_mock.patch.object(
            test_module.Conn23Record, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id:
            mock_conn_rec_retrieve_by_id.side_effect = StorageNotFoundError()

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.connections_remove(mock_req)

    async def test_connections_remove_x(self):
        context = RequestContext(base_context=InjectionContext(enforce_typing=False))
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": context,
        }
        mock_req.match_info = {"conn_id": "dummy"}
        mock_conn_rec = async_mock.MagicMock(
            delete_record=async_mock.CoroutineMock(
                side_effect=test_module.StorageError()
            )
        )

        with async_mock.patch.object(
            test_module.Conn23Record, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id:
            mock_conn_rec_retrieve_by_id.return_value = mock_conn_rec

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.connections_remove(mock_req)

    async def test_register(self):
        mock_app = async_mock.MagicMock()
        mock_app.add_routes = async_mock.MagicMock()

        await test_module.register(mock_app)
        mock_app.add_routes.assert_called_once()

    async def test_post_process_routes(self):
        mock_app = async_mock.MagicMock(_state={"swagger_dict": {}})
        test_module.post_process_routes(mock_app)
        assert "tags" in mock_app._state["swagger_dict"]
