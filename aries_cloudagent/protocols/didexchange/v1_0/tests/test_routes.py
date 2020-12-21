from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from .....admin.request_context import AdminRequestContext
from .....storage.error import StorageNotFoundError

from .. import routes as test_module


class TestDIDExchangeConnRoutes(AsyncTestCase):
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

    """
    async def test_didx_list(self):
        context = RequestContext(base_context=InjectionContext(enforce_typing=False))
        context.default_endpoint = "http://1.2.3.4:8081"  # for coverage
        assert context.default_endpoint == "http://1.2.3.4:8081"  # for coverage
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": context,
        }
        mock_req.query = {
            "invitation_id": "dummy",  # exercise tag filter assignment
            "their_role": ConnRecord.Role.REQUESTER.rfc23,
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
                await test_module.didx_connections_list(mock_req)
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

    async def test_didx_list_x(self):
        context = RequestContext(base_context=InjectionContext(enforce_typing=False))
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": context,
        }
        mock_req.query = {
            "their_role": ConnRecord.Role.REQUESTER.rfc23,
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
                await test_module.didx_connections_list(mock_req)

    async def test_retrieve_connection(self):
        context = RequestContext(base_context=InjectionContext(enforce_typing=False))
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": context,
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

            await test_module.didx_retrieve_connection(mock_req)
            mock_response.assert_called_once_with({"hello": "world"})

    async def test_retrieve_connection_not_found_x(self):
        context = RequestContext(base_context=InjectionContext(enforce_typing=False))
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": context,
        }
        mock_req.match_info = {"conn_id": "dummy"}

        with async_mock.patch.object(
            test_module.ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id:
            mock_conn_rec_retrieve_by_id.side_effect = StorageNotFoundError()

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.didx_retrieve_connection(mock_req)

    async def test_retrieve_connection_base_model_x(self):
        context = RequestContext(base_context=InjectionContext(enforce_typing=False))
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": context,
        }
        mock_req.match_info = {"conn_id": "dummy"}

        with async_mock.patch.object(
            test_module.ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id:
            mock_conn_rec_retrieve_by_id.return_value = async_mock.MagicMock(
                serialize=async_mock.MagicMock(side_effect=test_module.BaseModelError())
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.didx_retrieve_connection(mock_req)
    """

    async def test_didx_receive_invitation(self):
        self.request.json = async_mock.CoroutineMock()
        self.request.query = {
            "auto_accept": "true",
            "alias": "alias",
        }

        mock_conn_rec = async_mock.MagicMock()
        mock_conn_rec.serialize = async_mock.MagicMock()

        with async_mock.patch.object(
            test_module.OOBInvitation, "deserialize", autospec=True
        ) as mock_inv_deser, async_mock.patch.object(
            test_module, "DIDXManager", autospec=True
        ) as mock_didx_mgr, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_didx_mgr.return_value.receive_invitation = async_mock.CoroutineMock(
                return_value=mock_conn_rec
            )

            await test_module.didx_receive_invitation(self.request)
            mock_response.assert_called_once_with(mock_conn_rec.serialize.return_value)

    async def test_didx_receive_invitation_bad(self):
        self.request.json = async_mock.CoroutineMock()
        self.request.query = {
            "auto_accept": "true",
            "alias": "alias",
        }

        mock_conn_rec = async_mock.MagicMock()
        mock_conn_rec.serialize = async_mock.MagicMock()

        with async_mock.patch.object(
            test_module.OOBInvitation, "deserialize", autospec=True
        ) as mock_inv_deser, async_mock.patch.object(
            test_module, "DIDXManager", autospec=True
        ) as mock_didx_mgr:
            mock_inv_deser.side_effect = test_module.BaseModelError()

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.didx_receive_invitation(self.request)

    async def test_didx_receive_invitation_forbidden(self):
        self.context.update_settings({"admin.no_receive_invites": True})

        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.didx_receive_invitation(self.request)

    async def test_didx_accept_invitation(self):
        self.request.match_info = {"conn_id": "dummy"}
        self.request.query = {
            "my_label": "label",
            "my_endpoint": "http://endpoint.ca",
        }

        mock_conn_rec = async_mock.MagicMock(save=async_mock.CoroutineMock())
        mock_conn_rec.serialize = async_mock.MagicMock()

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec_class, async_mock.patch.object(
            test_module, "DIDXManager", autospec=True
        ) as mock_didx_mgr, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:

            mock_conn_rec_class.retrieve_by_id.return_value = mock_conn_rec
            mock_didx_mgr.return_value.create_request = async_mock.CoroutineMock()

            await test_module.didx_accept_invitation(self.request)
            mock_response.assert_called_once_with(mock_conn_rec.serialize.return_value)

    async def test_didx_accept_invitation_not_found(self):
        self.request.match_info = {"conn_id": "dummy"}

        with async_mock.patch.object(
            test_module.ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id:
            mock_conn_rec_retrieve_by_id.side_effect = StorageNotFoundError()

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.didx_accept_invitation(self.request)

    async def test_didx_accept_invitation_x(self):
        self.request.match_info = {"conn_id": "dummy"}

        with async_mock.patch.object(
            test_module.ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id, async_mock.patch.object(
            test_module, "DIDXManager", autospec=True
        ) as mock_didx_mgr:
            mock_didx_mgr.return_value.create_request = async_mock.CoroutineMock(
                side_effect=test_module.DIDXManagerError()
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.didx_accept_invitation(self.request)

    async def test_didx_accept_request(self):
        self.request.match_info = {"conn_id": "dummy"}
        self.request.query = {
            "my_endpoint": "http://endpoint.ca",
        }

        mock_conn_rec = async_mock.MagicMock()
        mock_conn_rec.serialize = async_mock.MagicMock()

        with async_mock.patch.object(
            test_module.ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id, async_mock.patch.object(
            test_module, "DIDXManager", autospec=True
        ) as mock_didx_mgr, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_conn_rec_retrieve_by_id.return_value = mock_conn_rec
            mock_didx_mgr.return_value.create_response = async_mock.CoroutineMock()

            await test_module.didx_accept_request(self.request)
            mock_response.assert_called_once_with(mock_conn_rec.serialize.return_value)

    async def test_didx_accept_request_not_found(self):
        self.request.match_info = {"conn_id": "dummy"}

        with async_mock.patch.object(
            test_module.ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id:
            mock_conn_rec_retrieve_by_id.side_effect = StorageNotFoundError()

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.didx_accept_request(self.request)

    async def test_didx_accept_request_x(self):
        self.request.match_info = {"conn_id": "dummy"}

        with async_mock.patch.object(
            test_module.ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id, async_mock.patch.object(
            test_module, "DIDXManager", autospec=True
        ) as mock_didx_mgr, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_didx_mgr.return_value.create_response = async_mock.CoroutineMock(
                side_effect=test_module.DIDXManagerError()
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.didx_accept_request(self.request)

    """
    async def test_didx_establish_inbound(self):
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
            test_module.ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id, async_mock.patch.object(
            test_module, "DIDXManager", autospec=True
        ) as mock_didx_mgr, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_conn_rec_retrieve_by_id.return_value = mock_conn_rec
            mock_didx_mgr.return_value.establish_inbound = async_mock.CoroutineMock()

            await test_module.didx_establish_inbound(mock_req)
            mock_response.assert_called_once_with({})

    async def test_didx_establish_inbound_not_found(self):
        context = RequestContext(base_context=InjectionContext(enforce_typing=False))
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": context,
            "outbound_message_router": async_mock.CoroutineMock(),
        }
        mock_req.match_info = {"conn_id": "dummy", "ref_id": "ref"}

        with async_mock.patch.object(
            test_module.ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id:
            mock_conn_rec_retrieve_by_id.side_effect = StorageNotFoundError()

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.didx_establish_inbound(mock_req)

    async def test_didx_establish_inbound_x(self):
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
            test_module.ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id, async_mock.patch.object(
            test_module, "DIDXManager", autospec=True
        ) as mock_didx_mgr:
            mock_conn_rec_retrieve_by_id.return_value = mock_conn_rec
            mock_didx_mgr.return_value.establish_inbound = async_mock.CoroutineMock(
                side_effect=test_module.DIDXManagerError()
            )
            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.didx_establish_inbound(mock_req)
    """

    """
    async def test_didx_remove(self):
        context = RequestContext(base_context=InjectionContext(enforce_typing=False))
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": context,
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

            await test_module.didx_remove_connection(mock_req)
            mock_response.assert_called_once_with({})

    async def test_didx_remove_not_found(self):
        context = RequestContext(base_context=InjectionContext(enforce_typing=False))
        mock_req = async_mock.MagicMock()
        mock_req.app = {
            "request_context": context,
        }
        mock_req.match_info = {"conn_id": "dummy"}

        mock_conn_rec = async_mock.MagicMock()

        with async_mock.patch.object(
            test_module.ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id:
            mock_conn_rec_retrieve_by_id.side_effect = StorageNotFoundError()

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.didx_remove_connection(mock_req)

    async def test_didx_remove_x(self):
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
            test_module.ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id:
            mock_conn_rec_retrieve_by_id.return_value = mock_conn_rec

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.didx_remove_connection(mock_req)
    """

    """
    async def test_didx_create_static(self):
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
                "their_label": "Clafouti Quasar",
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
            test_module, "DIDXManager", autospec=True
        ) as mock_didx_mgr, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_didx_mgr.return_value.create_static_connection = (
                async_mock.CoroutineMock(
                    return_value=(mock_my_info, mock_their_info, mock_conn_rec)
                )
            )

            await test_module.didx_create_static(mock_req)
            mock_response.assert_called_once_with(
                {
                    "my_did": mock_my_info.did,
                    "my_verkey": mock_my_info.verkey,
                    "my_endpoint": context.settings.get("default_endpoint"),
                    "their_did": mock_their_info.did,
                    "their_verkey": mock_their_info.verkey,
                    "record": mock_conn_rec.serialize.return_value,
                }
            )

    async def test_didx_create_static_x(self):
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
                "their_label": "Clafouti Quasar",
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
            test_module, "DIDXManager", autospec=True
        ) as mock_didx_mgr:
            mock_didx_mgr.return_value.create_static_connection = (
                async_mock.CoroutineMock(side_effect=test_module.WalletError())
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.didx_create_static(mock_req)
    """

    async def test_register(self):
        mock_app = async_mock.MagicMock()
        mock_app.add_routes = async_mock.MagicMock()

        await test_module.register(mock_app)
        mock_app.add_routes.assert_called_once()

    async def test_post_process_routes(self):
        mock_app = async_mock.MagicMock(_state={"swagger_dict": {}})
        test_module.post_process_routes(mock_app)
        assert "tags" in mock_app._state["swagger_dict"]
