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

    async def test_didx_create_request_implicit(self):
        self.request.query = {
            "their_public_did": "public-did",
            "my_label": "label baby junior",
            "my_endpoint": "http://endpoint.ca",
        }

        with async_mock.patch.object(
            test_module, "DIDXManager", autospec=True
        ) as mock_didx_mgr, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_didx_mgr.return_value.create_request_implicit = (
                async_mock.CoroutineMock(
                    return_value=async_mock.MagicMock(
                        serialize=async_mock.MagicMock(
                            return_value="mock serialization"
                        )
                    )
                )
            )

            await test_module.didx_request_implicit(self.request)
            mock_response.assert_called_once_with("mock serialization")

    async def test_didx_create_request_implicit_not_found_x(self):
        self.request.query = {
            "their_public_did": "public-did",
            "my_label": "label baby junior",
            "my_endpoint": "http://endpoint.ca",
        }

        with async_mock.patch.object(
            test_module, "DIDXManager", autospec=True
        ) as mock_didx_mgr, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_didx_mgr.return_value.create_request_implicit = (
                async_mock.CoroutineMock(side_effect=StorageNotFoundError("not found"))
            )

            with self.assertRaises(test_module.web.HTTPNotFound) as context:
                await test_module.didx_request_implicit(self.request)
            assert "not found" in str(context.exception)

    async def test_didx_request_wallet_x(self):
        self.request.query = {
            "their_public_did": "public-did",
            "my_label": "label baby junior",
            "my_endpoint": "http://endpoint.ca",
        }

        with async_mock.patch.object(
            test_module, "DIDXManager", autospec=True
        ) as mock_didx_mgr, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_didx_mgr.return_value.create_request_implicit = (
                async_mock.CoroutineMock(
                    side_effect=test_module.WalletError("wallet error")
                )
            )

            with self.assertRaises(test_module.web.HTTPBadRequest) as context:
                await test_module.didx_request_implicit(self.request)
            assert "wallet error" in str(context.exception)

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
