from unittest import IsolatedAsyncioTestCase
from aries_cloudagent.tests import mock

from .. import routes as test_module
from .....admin.request_context import AdminRequestContext
from .....storage.error import StorageNotFoundError
from ....coordinate_mediation.v1_0.route_manager import RouteManager


class TestDIDExchangeConnRoutes(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.session_inject = {}
        self.context = AdminRequestContext.test_context(self.session_inject)
        self.profile = self.context.profile
        self.request_dict = {
            "context": self.context,
            "outbound_message_router": mock.CoroutineMock(),
        }
        self.request = mock.MagicMock(
            app={},
            match_info={},
            query={},
            __getitem__=lambda _, k: self.request_dict[k],
        )
        self.profile.context.injector.bind_instance(RouteManager, mock.MagicMock())

    async def test_didx_accept_invitation(self):
        self.request.match_info = {"conn_id": "dummy"}
        self.request.query = {
            "my_label": "label",
            "my_endpoint": "http://endpoint.ca",
        }

        mock_conn_rec = mock.MagicMock(save=mock.CoroutineMock())
        mock_conn_rec.serialize = mock.MagicMock()

        with mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec_class, mock.patch.object(
            test_module, "DIDXManager", autospec=True
        ) as mock_didx_mgr, mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_conn_rec_class.retrieve_by_id.return_value = mock_conn_rec
            mock_didx_mgr.return_value.create_request = mock.CoroutineMock()

            await test_module.didx_accept_invitation(self.request)
            mock_response.assert_called_once_with(mock_conn_rec.serialize.return_value)

    async def test_didx_accept_invitation_not_found(self):
        self.request.match_info = {"conn_id": "dummy"}

        with mock.patch.object(
            test_module.ConnRecord, "retrieve_by_id", mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id:
            mock_conn_rec_retrieve_by_id.side_effect = StorageNotFoundError()

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.didx_accept_invitation(self.request)

    async def test_didx_accept_invitation_x(self):
        self.request.match_info = {"conn_id": "dummy"}

        with mock.patch.object(
            test_module.ConnRecord, "retrieve_by_id", mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id, mock.patch.object(
            test_module, "DIDXManager", autospec=True
        ) as mock_didx_mgr:
            mock_didx_mgr.return_value.create_request = mock.CoroutineMock(
                side_effect=test_module.DIDXManagerError()
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.didx_accept_invitation(self.request)

    async def test_didx_create_request_implicit(self):
        self.request.query = {
            "their_public_did": "public-did",
            "my_label": "label baby junior",
            "my_endpoint": "http://endpoint.ca",
            "mediator_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        }

        with mock.patch.object(
            test_module, "DIDXManager", autospec=True
        ) as mock_didx_mgr, mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_didx_mgr.return_value.create_request_implicit = mock.CoroutineMock(
                return_value=mock.MagicMock(
                    serialize=mock.MagicMock(return_value="mock serialization")
                )
            )

            await test_module.didx_create_request_implicit(self.request)
            mock_response.assert_called_once_with("mock serialization")

    async def test_didx_create_request_implicit_not_found_x(self):
        self.request.query = {
            "their_public_did": "public-did",
            "my_label": "label baby junior",
            "my_endpoint": "http://endpoint.ca",
            "mediator_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "auto_accept": "true",
        }

        with mock.patch.object(
            test_module, "DIDXManager", autospec=True
        ) as mock_didx_mgr, mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_didx_mgr.return_value.create_request_implicit = mock.CoroutineMock(
                side_effect=StorageNotFoundError("not found")
            )

            with self.assertRaises(test_module.web.HTTPNotFound) as context:
                await test_module.didx_create_request_implicit(self.request)
            assert "not found" in str(context.exception)

    async def test_didx_create_request_implicit_wallet_x(self):
        self.request.query = {
            "their_public_did": "public-did",
            "my_label": "label baby junior",
            "my_endpoint": "http://endpoint.ca",
            "auto_accept": "true",
        }

        with mock.patch.object(
            test_module, "DIDXManager", autospec=True
        ) as mock_didx_mgr, mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_didx_mgr.return_value.create_request_implicit = mock.CoroutineMock(
                side_effect=test_module.WalletError("wallet error")
            )

            with self.assertRaises(test_module.web.HTTPBadRequest) as context:
                await test_module.didx_create_request_implicit(self.request)
            assert "wallet error" in str(context.exception)

    async def test_didx_receive_request_implicit(self):
        self.request.query = {
            "alias": "Jimmy",
            "my_endpoint": "http://endpoint.ca",
        }
        self.request._thread.pthid = "did:sov:0000000000000000000000"
        self.request.json = mock.CoroutineMock()

        mock_conn_rec = mock.MagicMock()
        mock_conn_rec.serialize = mock.MagicMock()

        with mock.patch.object(
            test_module.DIDXRequest, "deserialize", mock.MagicMock()
        ) as mock_didx_req_deser, mock.patch.object(
            test_module, "DIDXManager", autospec=True
        ) as mock_didx_mgr, mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_didx_mgr.return_value.receive_request = mock.CoroutineMock(
                return_value=mock_conn_rec
            )

            await test_module.didx_receive_request_implicit(self.request)
            mock_response.assert_called_once_with(mock_conn_rec.serialize.return_value)

    async def test_didx_receive_request_implicit_not_found_x(self):
        self.request.query = {
            "alias": "Jimmy",
            "my_endpoint": "http://endpoint.ca",
        }
        self.request._thread.pthid = "did:sov:0000000000000000000000"
        self.request.json = mock.CoroutineMock()

        with mock.patch.object(
            test_module.DIDXRequest, "deserialize", mock.MagicMock()
        ) as mock_didx_req_deser, mock.patch.object(
            test_module, "DIDXManager", autospec=True
        ) as mock_didx_mgr, mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_didx_mgr.return_value.receive_request = mock.CoroutineMock(
                side_effect=StorageNotFoundError("tricorder must be broken")
            )

            with self.assertRaises(test_module.web.HTTPNotFound) as context:
                await test_module.didx_receive_request_implicit(self.request)
            assert "tricorder must be broken" in str(context.exception)

    async def test_didx_receive_request_implicit_bad_request_x(self):
        self.request.query = {
            "alias": "Jimmy",
            "my_endpoint": "http://endpoint.ca",
        }
        self.request._thread.pthid = "did:sov:0000000000000000000000"
        self.request.json = mock.CoroutineMock()

        with mock.patch.object(
            test_module.DIDXRequest, "deserialize", mock.MagicMock()
        ) as mock_didx_req_deser, mock.patch.object(
            test_module, "DIDXManager", autospec=True
        ) as mock_didx_mgr, mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_didx_req_deser.side_effect = test_module.BaseModelError("bad bits")
            with self.assertRaises(test_module.web.HTTPBadRequest) as context:
                await test_module.didx_receive_request_implicit(self.request)
            assert "bad bits" in str(context.exception)

    async def test_didx_accept_request(self):
        self.request.match_info = {"conn_id": "dummy"}
        self.request.query = {
            "my_endpoint": "http://endpoint.ca",
        }

        mock_conn_rec = mock.MagicMock()
        mock_conn_rec.serialize = mock.MagicMock()

        with mock.patch.object(
            test_module.ConnRecord, "retrieve_by_id", mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id, mock.patch.object(
            test_module, "DIDXManager", autospec=True
        ) as mock_didx_mgr, mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_conn_rec_retrieve_by_id.return_value = mock_conn_rec
            mock_didx_mgr.return_value.create_response = mock.CoroutineMock()

            await test_module.didx_accept_request(self.request)
            mock_response.assert_called_once_with(mock_conn_rec.serialize.return_value)

    async def test_didx_accept_request_not_found(self):
        self.request.match_info = {"conn_id": "dummy"}

        with mock.patch.object(
            test_module.ConnRecord, "retrieve_by_id", mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id:
            mock_conn_rec_retrieve_by_id.side_effect = StorageNotFoundError()

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.didx_accept_request(self.request)

    async def test_didx_accept_request_x(self):
        self.request.match_info = {"conn_id": "dummy"}

        with mock.patch.object(
            test_module.ConnRecord, "retrieve_by_id", mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id, mock.patch.object(
            test_module, "DIDXManager", autospec=True
        ) as mock_didx_mgr, mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_didx_mgr.return_value.create_response = mock.CoroutineMock(
                side_effect=test_module.DIDXManagerError()
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.didx_accept_request(self.request)

    async def test_didx_reject(self):
        self.request.match_info = {"conn_id": "dummy"}
        self.request.json = mock.CoroutineMock(return_value={"reason": "asdf"})

        with mock.patch.object(
            test_module.ConnRecord, "retrieve_by_id", mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id, mock.patch.object(
            test_module, "DIDXManager", autospec=True
        ) as mock_didx_mgr, mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_didx_mgr.return_value.reject = mock.CoroutineMock()

            await test_module.didx_reject(self.request)

    async def test_didx_reject_x_not_found(self):
        self.request.match_info = {"conn_id": "dummy"}
        self.request.json = mock.CoroutineMock(return_value={"reason": "asdf"})

        with mock.patch.object(
            test_module.ConnRecord, "retrieve_by_id", mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id:
            mock_conn_rec_retrieve_by_id.side_effect = StorageNotFoundError()

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.didx_reject(self.request)

    async def test_didx_reject_x_bad_conn_state(self):
        self.request.match_info = {"conn_id": "dummy"}
        self.request.json = mock.CoroutineMock(return_value={"reason": "asdf"})

        with mock.patch.object(
            test_module.ConnRecord, "retrieve_by_id", mock.CoroutineMock()
        ) as mock_conn_rec_retrieve_by_id, mock.patch.object(
            test_module, "DIDXManager", autospec=True
        ) as mock_didx_mgr, mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_didx_mgr.return_value.reject = mock.CoroutineMock(
                side_effect=test_module.DIDXManagerError()
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.didx_reject(self.request)

    async def test_register(self):
        mock_app = mock.MagicMock()
        mock_app.add_routes = mock.MagicMock()

        await test_module.register(mock_app)
        mock_app.add_routes.assert_called_once()

    async def test_post_process_routes(self):
        mock_app = mock.MagicMock(_state={"swagger_dict": {}})
        test_module.post_process_routes(mock_app)
        assert "tags" in mock_app._state["swagger_dict"]
