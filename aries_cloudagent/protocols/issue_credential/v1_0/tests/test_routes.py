from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from .....admin.request_context import AdminRequestContext
from .....wallet.base import BaseWallet, DIDInfo

from .. import routes as test_module


class TestCredentialRoutes(AsyncTestCase):
    async def setUp(self):
        self.session_inject = {}
        self.context = AdminRequestContext.test_context(self.session_inject)
        self.request_dict = {"context": self.context}
        self.request = async_mock.MagicMock(
            app={"outbound_message_router": async_mock.CoroutineMock()},
            match_info={},
            query={},
            __getitem__=lambda _, k: self.request_dict[k],
        )

    async def test_credential_exchange_list(self):
        self.request.query = {
            "thread_id": "dummy",
            "connection_id": "dummy",
            "role": "dummy",
            "state": "dummy",
        }

        with async_mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex:
            mock_cred_ex.query = async_mock.CoroutineMock()
            mock_cred_ex.query.return_value = [mock_cred_ex]
            mock_cred_ex.serialize = async_mock.MagicMock()
            mock_cred_ex.serialize.return_value = {"hello": "world"}

            with async_mock.patch.object(
                test_module.web, "json_response"
            ) as mock_response:
                await test_module.credential_exchange_list(self.request)
                mock_response.assert_called_once_with(
                    {"results": [mock_cred_ex.serialize.return_value]}
                )

    async def test_credential_exchange_list_x(self):
        self.request.query = {
            "thread_id": "dummy",
            "connection_id": "dummy",
            "role": "dummy",
            "state": "dummy",
        }

        with async_mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex:
            mock_cred_ex.connection_id = "conn-123"
            mock_cred_ex.thread_id = "conn-123"
            mock_cred_ex.query = async_mock.CoroutineMock(
                side_effect=test_module.StorageError()
            )
            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_list(self.request)

    async def test_credential_exchange_retrieve(self):
        self.request.match_info = {"cred_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex:
            mock_cred_ex.connection_id = "conn-123"
            mock_cred_ex.thread_id = "conn-123"
            mock_cred_ex.retrieve_by_id = async_mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.return_value = mock_cred_ex
            mock_cred_ex.serialize = async_mock.MagicMock()
            mock_cred_ex.serialize.return_value = {"hello": "world"}

            with async_mock.patch.object(
                test_module.web, "json_response"
            ) as mock_response:
                await test_module.credential_exchange_retrieve(self.request)
                mock_response.assert_called_once_with(
                    mock_cred_ex.serialize.return_value
                )

    async def test_credential_exchange_retrieve_not_found(self):
        self.request.match_info = {"cred_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex:
            mock_cred_ex.connection_id = "conn-123"
            mock_cred_ex.thread_id = "conn-123"
            mock_cred_ex.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=test_module.StorageNotFoundError()
            )
            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.credential_exchange_retrieve(self.request)

    async def test_credential_exchange_retrieve_x(self):
        self.request.match_info = {"cred_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex:
            mock_cred_ex.connection_id = "conn-123"
            mock_cred_ex.thread_id = "conn-123"
            mock_cred_ex.retrieve_by_id = async_mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.return_value = mock_cred_ex
            mock_cred_ex.serialize = async_mock.MagicMock(
                side_effect=test_module.BaseModelError()
            )
            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_retrieve(self.request)

    async def test_credential_exchange_create(self):
        self.request.json = async_mock.CoroutineMock()

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "CredentialManager", autospec=True
        ) as mock_credential_manager, async_mock.patch.object(
            test_module.CredentialPreview, "deserialize", autospec=True
        ), async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_credential_manager.return_value.create_offer = (
                async_mock.CoroutineMock()
            )

            mock_credential_manager.return_value.create_offer.return_value = (
                async_mock.CoroutineMock(),
                async_mock.CoroutineMock(),
            )

            mock_cred_ex_record = async_mock.MagicMock()
            mock_cred_offer = async_mock.MagicMock()

            mock_credential_manager.return_value.prepare_send.return_value = (
                mock_cred_ex_record,
                mock_cred_offer,
            )

            await test_module.credential_exchange_create(self.request)

            mock_response.assert_called_once_with(
                mock_cred_ex_record.serialize.return_value
            )

    async def test_credential_exchange_create_x(self):
        self.request.json = async_mock.CoroutineMock()

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "CredentialManager", autospec=True
        ) as mock_credential_manager, async_mock.patch.object(
            test_module.CredentialPreview, "deserialize", autospec=True
        ), async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_credential_manager.return_value.create_offer = (
                async_mock.CoroutineMock()
            )

            mock_credential_manager.return_value.create_offer.return_value = (
                async_mock.CoroutineMock(),
                async_mock.CoroutineMock(),
            )

            mock_cred_ex_record = async_mock.MagicMock()
            mock_cred_offer = async_mock.MagicMock()

            mock_credential_manager.return_value.prepare_send.side_effect = (
                test_module.StorageError()
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_create(self.request)

    async def test_credential_exchange_create_no_proposal(self):
        conn_id = "connection-id"

        self.request.json = async_mock.CoroutineMock(
            return_value={"connection_id": conn_id}
        )

        with self.assertRaises(test_module.web.HTTPBadRequest) as context:
            await test_module.credential_exchange_create(self.request)
        assert "credential_proposal" in str(context.exception)

    async def test_credential_exchange_send(self):
        self.request.json = async_mock.CoroutineMock()

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec, async_mock.patch.object(
            test_module, "CredentialManager", autospec=True
        ) as mock_credential_manager, async_mock.patch.object(
            test_module.CredentialPreview, "deserialize", autospec=True
        ), async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_credential_manager.return_value.create_offer = (
                async_mock.CoroutineMock()
            )

            mock_credential_manager.return_value.create_offer.return_value = (
                async_mock.CoroutineMock(),
                async_mock.CoroutineMock(),
            )

            mock_cred_ex_record = async_mock.MagicMock()
            mock_cred_offer = async_mock.MagicMock()

            mock_credential_manager.return_value.prepare_send.return_value = (
                mock_cred_ex_record,
                mock_cred_offer,
            )

            await test_module.credential_exchange_send(self.request)

            mock_response.assert_called_once_with(
                mock_cred_ex_record.serialize.return_value
            )

    async def test_credential_exchange_send_no_proposal(self):
        conn_id = "connection-id"

        self.request.json = async_mock.CoroutineMock(
            return_value={"connection_id": conn_id}
        )

        with self.assertRaises(test_module.web.HTTPBadRequest) as context:
            await test_module.credential_exchange_send(self.request)
        assert "credential_proposal" in str(context.exception)

    async def test_credential_exchange_send_no_conn_record(self):
        conn_id = "connection-id"
        preview_spec = {"attributes": [{"name": "attr", "value": "value"}]}

        self.request.json = async_mock.CoroutineMock(
            return_value={"connection_id": conn_id, "credential_proposal": preview_spec}
        )

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec, async_mock.patch.object(
            test_module, "CredentialManager", autospec=True
        ) as mock_credential_manager:

            # Emulate storage not found (bad connection id)
            mock_conn_rec.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=test_module.StorageNotFoundError()
            )

            mock_credential_manager.return_value.create_offer.return_value = (
                async_mock.MagicMock(),
                async_mock.MagicMock(),
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_send(self.request)

    async def test_credential_exchange_send_not_ready(self):
        conn_id = "connection-id"
        preview_spec = {"attributes": [{"name": "attr", "value": "value"}]}

        self.request.json = async_mock.CoroutineMock(
            return_value={"connection_id": conn_id, "credential_proposal": preview_spec}
        )

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec, async_mock.patch.object(
            test_module, "CredentialManager", autospec=True
        ) as mock_credential_manager:

            # Emulate connection not ready
            mock_conn_rec.retrieve_by_id.return_value.is_ready = False

            mock_credential_manager.return_value.create_offer.return_value = (
                async_mock.MagicMock(),
                async_mock.MagicMock(),
            )

            with self.assertRaises(test_module.web.HTTPForbidden):
                await test_module.credential_exchange_send(self.request)

    async def test_credential_exchange_send_proposal(self):
        conn_id = "connection-id"
        preview_spec = {"attributes": [{"name": "attr", "value": "value"}]}

        self.request.json = async_mock.CoroutineMock(
            return_value={"connection_id": conn_id, "credential_proposal": preview_spec}
        )

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec, async_mock.patch.object(
            test_module, "CredentialManager", autospec=True
        ) as mock_credential_manager, async_mock.patch.object(
            test_module.CredentialProposal, "deserialize", autospec=True
        ) as mock_proposal_deserialize, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:

            mock_cred_ex_record = async_mock.MagicMock()

            mock_credential_manager.return_value.create_proposal.return_value = (
                mock_cred_ex_record
            )

            await test_module.credential_exchange_send_proposal(self.request)

            mock_response.assert_called_once_with(
                mock_cred_ex_record.serialize.return_value
            )

            self.request.app["outbound_message_router"].assert_awaited_once_with(
                mock_proposal_deserialize.return_value, connection_id=conn_id
            )

    async def test_credential_exchange_send_proposal_no_conn_record(self):
        self.request.json = async_mock.CoroutineMock()

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec, async_mock.patch.object(
            test_module, "CredentialManager", autospec=True
        ) as mock_credential_manager, async_mock.patch.object(
            test_module.CredentialPreview, "deserialize", autospec=True
        ) as mock_preview_deserialize:

            # Emulate storage not found (bad connection id)
            mock_conn_rec.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=test_module.StorageNotFoundError()
            )

            mock_credential_manager.return_value.create_proposal.return_value = (
                async_mock.MagicMock()
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_send_proposal(self.request)

    async def test_credential_exchange_send_proposal_deser_x(self):
        conn_id = "connection-id"
        preview_spec = {"attributes": [{"name": "attr", "value": "value"}]}

        self.request.json = async_mock.CoroutineMock(
            return_value={"connection_id": conn_id, "credential_proposal": preview_spec}
        )

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec, async_mock.patch.object(
            test_module, "CredentialManager", autospec=True
        ) as mock_credential_manager, async_mock.patch.object(
            test_module.CredentialProposal, "deserialize", autospec=True
        ) as mock_proposal_deserialize:
            mock_cred_ex_record = async_mock.MagicMock()
            mock_credential_manager.return_value.create_proposal.return_value = (
                mock_cred_ex_record
            )
            mock_proposal_deserialize.side_effect = test_module.BaseModelError()
            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_send_proposal(self.request)

    async def test_credential_exchange_send_proposal_not_ready(self):
        self.request.json = async_mock.CoroutineMock()

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec, async_mock.patch.object(
            test_module, "CredentialManager", autospec=True
        ) as mock_credential_manager, async_mock.patch.object(
            test_module.CredentialPreview, "deserialize", autospec=True
        ) as mock_preview_deserialize:

            # Emulate connection not ready
            mock_conn_rec.retrieve_by_id = async_mock.CoroutineMock()
            mock_conn_rec.retrieve_by_id.return_value.is_ready = False

            mock_credential_manager.return_value.create_proposal.return_value = (
                async_mock.MagicMock()
            )

            with self.assertRaises(test_module.web.HTTPForbidden):
                await test_module.credential_exchange_send_proposal(self.request)

    async def test_credential_exchange_create_free_offer(self):
        self.request.json = async_mock.CoroutineMock(
            return_value={
                "auto_issue": False,
                "cred_def_id": "cred-def-id",
                "connection_id": "dummy",
                "credential_preview": {
                    "attributes": [{"name": "hello", "value": "world"}]
                },
            }
        )

        self.context.update_settings({"default_endpoint": "http://1.2.3.4:8081"})
        self.session_inject[BaseWallet] = async_mock.MagicMock(
            get_local_did=async_mock.CoroutineMock(
                return_value=DIDInfo("did", "verkey", {"meta": "data"})
            ),
            get_public_did=async_mock.CoroutineMock(
                return_value=DIDInfo("public-did", "verkey", {"meta": "data"})
            ),
        )

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec, async_mock.patch.object(
            test_module, "CredentialManager", autospec=True
        ) as mock_credential_manager, async_mock.patch.object(
            test_module, "serialize_outofband"
        ) as mock_seroob, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_credential_manager.return_value.create_offer = (
                async_mock.CoroutineMock()
            )
            mock_cred_ex_record = async_mock.MagicMock()
            mock_credential_manager.return_value.create_offer.return_value = (
                mock_cred_ex_record,
                async_mock.MagicMock(),
            )
            mock_seroob.return_value = "abc123"

            await test_module.credential_exchange_create_free_offer(self.request)

            mock_response.assert_called_once_with(
                {
                    "record": mock_cred_ex_record.serialize.return_value,
                    "oob_url": "abc123",
                }
            )

    async def test_credential_exchange_create_free_offer_no_cred_def_id(self):
        self.request.json = async_mock.CoroutineMock(
            return_value={
                "auto_issue": False,
                "connection_id": "dummy",
                "credential_preview": {
                    "attributes": [{"name": "hello", "value": "world"}]
                },
            }
        )

        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.credential_exchange_create_free_offer(self.request)

    async def test_credential_exchange_create_free_offer_no_preview(self):
        self.request.json = async_mock.CoroutineMock()
        self.request.json.return_value = {"comment": "comment", "cred_def_id": "dummy"}

        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.credential_exchange_create_free_offer(self.request)

    async def test_credential_exchange_create_free_offer_retrieve_conn_rec_x(self):
        self.request.json = async_mock.CoroutineMock(
            return_value={
                "auto_issue": False,
                "cred_def_id": "cred-def-id",
                "connection_id": "dummy",
                "credential_preview": {
                    "attributes": [{"name": "hello", "value": "world"}]
                },
            }
        )

        self.session_inject[BaseWallet] = async_mock.MagicMock(
            get_local_did=async_mock.CoroutineMock(
                side_effect=test_module.WalletError()
            ),
        )

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec:
            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_create_free_offer(self.request)

    async def test_credential_exchange_create_free_offer_no_conn_id(self):
        self.request.json = async_mock.CoroutineMock(
            return_value={
                "auto_issue": False,
                "cred_def_id": "cred-def-id",
                "credential_preview": {
                    "attributes": [{"name": "hello", "value": "world"}]
                },
            }
        )

        self.context.update_settings({"default_endpoint": "http://1.2.3.4:8081"})
        self.session_inject[BaseWallet] = async_mock.MagicMock(
            get_public_did=async_mock.CoroutineMock(
                return_value=DIDInfo("public-did", "verkey", {"meta": "data"})
            ),
            get_local_did=async_mock.CoroutineMock(
                return_value=DIDInfo("did", "verkey", {"meta": "data"})
            ),
        )

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec, async_mock.patch.object(
            test_module, "CredentialManager", autospec=True
        ) as mock_credential_manager, async_mock.patch.object(
            test_module, "serialize_outofband"
        ) as mock_seroob, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:

            mock_credential_manager.return_value.create_offer = (
                async_mock.CoroutineMock()
            )

            mock_cred_ex_record = async_mock.MagicMock()

            mock_credential_manager.return_value.create_offer.return_value = (
                mock_cred_ex_record,
                async_mock.MagicMock(),
            )

            mock_seroob.return_value = "abc123"

            await test_module.credential_exchange_create_free_offer(self.request)

            mock_response.assert_called_once_with(
                {
                    "record": mock_cred_ex_record.serialize.return_value,
                    "oob_url": "abc123",
                }
            )

    async def test_credential_exchange_create_free_offer_no_conn_id_no_public_did(self):
        self.request.json = async_mock.CoroutineMock(
            return_value={
                "auto_issue": False,
                "cred_def_id": "cred-def-id",
                "credential_preview": {
                    "attributes": [{"name": "hello", "value": "world"}]
                },
            }
        )

        self.context.update_settings({"default_endpoint": "http://1.2.3.4:8081"})
        self.session_inject[BaseWallet] = async_mock.MagicMock(
            get_public_did=async_mock.CoroutineMock(return_value=None),
        )

        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.credential_exchange_create_free_offer(self.request)

    async def test_credential_exchange_create_free_offer_no_endpoint(self):
        self.request.json = async_mock.CoroutineMock(
            return_value={
                "auto_issue": False,
                "cred_def_id": "cred-def-id",
                "credential_preview": {
                    "attributes": [{"name": "hello", "value": "world"}]
                },
            }
        )

        self.session_inject[BaseWallet] = async_mock.MagicMock(
            get_public_did=async_mock.CoroutineMock(
                return_value=DIDInfo("did", "verkey", {"meta": "data"})
            ),
        )

        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.credential_exchange_create_free_offer(self.request)

    async def test_credential_exchange_create_free_offer_deser_x(self):
        self.request.json = async_mock.CoroutineMock(
            return_value={
                "auto_issue": False,
                "cred_def_id": "cred-def-id",
                "connection_id": "dummy",
                "credential_preview": {
                    "attributes": [{"name": "hello", "value": "world"}]
                },
            }
        )

        self.context.update_settings({"default_endpoint": "http://1.2.3.4:8081"})
        self.session_inject[BaseWallet] = async_mock.MagicMock(
            get_local_did=async_mock.CoroutineMock(
                return_value=DIDInfo("did", "verkey", {"meta": "data"})
            ),
            get_public_did=async_mock.CoroutineMock(
                return_value=DIDInfo("public-did", "verkey", {"meta": "data"})
            ),
        )

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec, async_mock.patch.object(
            test_module, "CredentialManager", autospec=True
        ) as mock_credential_manager:
            mock_credential_manager.return_value.create_offer = (
                async_mock.CoroutineMock()
            )
            mock_cred_ex_record = async_mock.MagicMock()
            mock_credential_manager.return_value.create_offer.side_effect = (
                test_module.BaseModelError()
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_create_free_offer(self.request)

    async def test_credential_exchange_send_free_offer(self):
        self.request.json = async_mock.CoroutineMock(
            return_value={
                "auto_issue": False,
                "cred_def_id": "cred-def-id",
                "credential_preview": {
                    "attributes": [{"name": "hello", "value": "world"}]
                },
            }
        )

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec, async_mock.patch.object(
            test_module, "CredentialManager", autospec=True
        ) as mock_credential_manager, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:

            mock_credential_manager.return_value.create_offer = (
                async_mock.CoroutineMock()
            )

            mock_cred_ex_record = async_mock.MagicMock()

            mock_credential_manager.return_value.create_offer.return_value = (
                mock_cred_ex_record,
                async_mock.MagicMock(),
            )

            await test_module.credential_exchange_send_free_offer(self.request)

            mock_response.assert_called_once_with(
                mock_cred_ex_record.serialize.return_value
            )

    async def test_credential_exchange_send_free_offer_no_cred_def_id(self):
        self.request.json = async_mock.CoroutineMock()
        self.request.json.return_value = {
            "comment": "comment",
            "credential_preview": "dummy",
        }

        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.credential_exchange_send_free_offer(self.request)

    async def test_credential_exchange_send_free_offer_no_preview(self):
        self.request.json = async_mock.CoroutineMock()
        self.request.json.return_value = {"comment": "comment", "cred_def_id": "dummy"}

        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.credential_exchange_send_free_offer(self.request)

    async def test_credential_exchange_send_free_offer_no_conn_record(self):
        self.request.json = async_mock.CoroutineMock(
            return_value={
                "auto_issue": False,
                "cred_def_id": "cred-def-id",
                "credential_preview": "dummy",
            }
        )

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec, async_mock.patch.object(
            test_module, "CredentialManager", autospec=True
        ) as mock_credential_manager:

            # Emulate storage not found (bad connection id)
            mock_conn_rec.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=test_module.StorageNotFoundError()
            )

            mock_credential_manager.return_value.create_offer = (
                async_mock.CoroutineMock()
            )
            mock_credential_manager.return_value.create_offer.return_value = (
                async_mock.MagicMock(),
                async_mock.MagicMock(),
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_send_free_offer(self.request)

    async def test_credential_exchange_send_free_offer_not_ready(self):
        self.request.json = async_mock.CoroutineMock()
        self.request.json.return_value["auto_issue"] = True

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec, async_mock.patch.object(
            test_module, "CredentialManager", autospec=True
        ) as mock_credential_manager:

            # Emulate connection not ready
            mock_conn_rec.retrieve_by_id = async_mock.CoroutineMock()
            mock_conn_rec.retrieve_by_id.return_value.is_ready = False

            mock_credential_manager.return_value.create_offer = (
                async_mock.CoroutineMock()
            )
            mock_credential_manager.return_value.create_offer.return_value = (
                async_mock.MagicMock(),
                async_mock.MagicMock(),
            )

            with self.assertRaises(test_module.web.HTTPForbidden):
                await test_module.credential_exchange_send_free_offer(self.request)

    async def test_credential_exchange_send_bound_offer(self):
        self.request.json = async_mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec, async_mock.patch.object(
            test_module, "CredentialManager", autospec=True
        ) as mock_credential_manager, async_mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:

            mock_cred_ex.retrieve_by_id = async_mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.return_value.state = (
                mock_cred_ex.STATE_PROPOSAL_RECEIVED
            )

            mock_credential_manager.return_value.create_offer = (
                async_mock.CoroutineMock()
            )

            mock_cred_ex_record = async_mock.MagicMock()

            mock_credential_manager.return_value.create_offer.return_value = (
                mock_cred_ex_record,
                async_mock.MagicMock(),
            )

            await test_module.credential_exchange_send_bound_offer(self.request)

            mock_response.assert_called_once_with(
                mock_cred_ex_record.serialize.return_value
            )

    async def test_credential_exchange_send_bound_offer_bad_cred_ex_id(self):
        self.request.json = async_mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex:
            mock_cred_ex.connection_id = "conn-123"
            mock_cred_ex.thread_id = "conn-123"
            mock_cred_ex.retrieve_by_id = async_mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.side_effect = test_module.StorageNotFoundError()

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.credential_exchange_send_bound_offer(self.request)

    async def test_credential_exchange_send_bound_offer_no_conn_record(self):
        self.request.json = async_mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec, async_mock.patch.object(
            test_module, "CredentialManager", autospec=True
        ) as mock_credential_manager, async_mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex:
            mock_cred_ex.connection_id = "conn-123"
            mock_cred_ex.thread_id = "conn-123"
            mock_cred_ex.retrieve_by_id = async_mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.return_value.state = (
                mock_cred_ex.STATE_PROPOSAL_RECEIVED
            )

            # Emulate storage not found (bad connection id)
            mock_conn_rec.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=test_module.StorageNotFoundError()
            )

            mock_credential_manager.return_value.create_offer = (
                async_mock.CoroutineMock()
            )
            mock_credential_manager.return_value.create_offer.return_value = (
                async_mock.MagicMock(),
                async_mock.MagicMock(),
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_send_bound_offer(self.request)

    async def test_credential_exchange_send_bound_offer_bad_state(self):
        self.request.json = async_mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex:
            mock_cred_ex.connection_id = "conn-123"
            mock_cred_ex.thread_id = "conn-123"
            mock_cred_ex.retrieve_by_id = async_mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.return_value.state = mock_cred_ex.STATE_ACKED

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_send_bound_offer(self.request)

    async def test_credential_exchange_send_bound_offer_not_ready(self):
        self.request.json = async_mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec, async_mock.patch.object(
            test_module, "CredentialManager", autospec=True
        ) as mock_credential_manager, async_mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex:
            mock_cred_ex.connection_id = "conn-123"
            mock_cred_ex.thread_id = "conn-123"
            mock_cred_ex.retrieve_by_id = async_mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.return_value.state = (
                mock_cred_ex.STATE_PROPOSAL_RECEIVED
            )

            # Emulate connection not ready
            mock_conn_rec.retrieve_by_id = async_mock.CoroutineMock()
            mock_conn_rec.retrieve_by_id.return_value.is_ready = False

            mock_credential_manager.return_value.create_offer = (
                async_mock.CoroutineMock()
            )
            mock_credential_manager.return_value.create_offer.return_value = (
                async_mock.MagicMock(),
                async_mock.MagicMock(),
            )

            with self.assertRaises(test_module.web.HTTPForbidden):
                await test_module.credential_exchange_send_bound_offer(self.request)

    async def test_credential_exchange_send_request(self):
        self.request.json = async_mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec, async_mock.patch.object(
            test_module, "CredentialManager", autospec=True
        ) as mock_credential_manager, async_mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:

            mock_cred_ex.retrieve_by_id = async_mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.return_value.state = (
                mock_cred_ex.STATE_OFFER_RECEIVED
            )

            mock_cred_ex_record = async_mock.MagicMock()

            mock_credential_manager.return_value.create_request.return_value = (
                mock_cred_ex_record,
                async_mock.MagicMock(),
            )

            await test_module.credential_exchange_send_request(self.request)

            mock_response.assert_called_once_with(
                mock_cred_ex_record.serialize.return_value
            )

    async def test_credential_exchange_send_request_bad_cred_ex_id(self):
        self.request.json = async_mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex:
            mock_cred_ex.connection_id = "conn-123"
            mock_cred_ex.thread_id = "conn-123"
            mock_cred_ex.retrieve_by_id = async_mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.side_effect = test_module.StorageNotFoundError()

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.credential_exchange_send_request(self.request)

    async def test_credential_exchange_send_request_no_conn_record(self):
        self.request.json = async_mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec, async_mock.patch.object(
            test_module, "CredentialManager", autospec=True
        ) as mock_credential_manager, async_mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex:
            mock_cred_ex.connection_id = "conn-123"
            mock_cred_ex.thread_id = "conn-123"
            mock_cred_ex.retrieve_by_id = async_mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.return_value.state = (
                mock_cred_ex.STATE_OFFER_RECEIVED
            )

            # Emulate storage not found (bad connection id)
            mock_conn_rec.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=test_module.StorageNotFoundError()
            )

            mock_credential_manager.return_value.create_offer = (
                async_mock.CoroutineMock()
            )
            mock_credential_manager.return_value.create_offer.return_value = (
                async_mock.MagicMock(),
                async_mock.MagicMock(),
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_send_request(self.request)

    async def test_credential_exchange_send_request_not_ready(self):
        self.request.json = async_mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec, async_mock.patch.object(
            test_module, "CredentialManager", autospec=True
        ) as mock_credential_manager, async_mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex:
            mock_cred_ex.connection_id = "conn-123"
            mock_cred_ex.thread_id = "conn-123"
            mock_cred_ex.retrieve_by_id = async_mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.return_value.state = (
                mock_cred_ex.STATE_OFFER_RECEIVED
            )

            # Emulate connection not ready
            mock_conn_rec.retrieve_by_id = async_mock.CoroutineMock()
            mock_conn_rec.retrieve_by_id.return_value.is_ready = False

            mock_credential_manager.return_value.create_offer = (
                async_mock.CoroutineMock()
            )
            mock_credential_manager.return_value.create_offer.return_value = (
                async_mock.MagicMock(),
                async_mock.MagicMock(),
            )

            with self.assertRaises(test_module.web.HTTPForbidden):
                await test_module.credential_exchange_send_request(self.request)

    async def test_credential_exchange_issue(self):
        self.request.json = async_mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec, async_mock.patch.object(
            test_module, "CredentialManager", autospec=True
        ) as mock_credential_manager, async_mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:

            mock_cred_ex.retrieve_by_id = async_mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.return_value.state = (
                mock_cred_ex.STATE_REQUEST_RECEIVED
            )

            mock_cred_ex_record = async_mock.MagicMock()

            mock_credential_manager.return_value.issue_credential.return_value = (
                mock_cred_ex_record,
                async_mock.MagicMock(),
            )

            await test_module.credential_exchange_issue(self.request)

            mock_response.assert_called_once_with(
                mock_cred_ex_record.serialize.return_value
            )

    async def test_credential_exchange_issue_bad_cred_ex_id(self):
        self.request.json = async_mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex:
            mock_cred_ex.connection_id = "conn-123"
            mock_cred_ex.thread_id = "conn-123"
            mock_cred_ex.retrieve_by_id = async_mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.side_effect = test_module.StorageNotFoundError()

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.credential_exchange_issue(self.request)

    async def test_credential_exchange_issue_no_conn_record(self):
        self.request.json = async_mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec, async_mock.patch.object(
            test_module, "CredentialManager", autospec=True
        ) as mock_credential_manager, async_mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex:

            mock_cred_ex.retrieve_by_id = async_mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.return_value.state = (
                mock_cred_ex.STATE_REQUEST_RECEIVED
            )

            # Emulate storage not found (bad connection id)
            mock_conn_rec.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=test_module.StorageNotFoundError()
            )

            mock_credential_manager.return_value.issue_credential = (
                async_mock.CoroutineMock()
            )
            mock_credential_manager.return_value.issue_credential.return_value = (
                async_mock.MagicMock(),
                async_mock.MagicMock(),
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_issue(self.request)

    async def test_credential_exchange_issue_not_ready(self):
        self.request.json = async_mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec, async_mock.patch.object(
            test_module, "CredentialManager", autospec=True
        ) as mock_credential_manager, async_mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex:

            mock_cred_ex.retrieve_by_id = async_mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.return_value.state = (
                mock_cred_ex.STATE_REQUEST_RECEIVED
            )

            # Emulate connection not ready
            mock_conn_rec.retrieve_by_id = async_mock.CoroutineMock()
            mock_conn_rec.retrieve_by_id.return_value.is_ready = False

            mock_credential_manager.return_value.issue_credential = (
                async_mock.CoroutineMock()
            )
            mock_credential_manager.return_value.issue_credential.return_value = (
                async_mock.MagicMock(),
                async_mock.MagicMock(),
            )

            with self.assertRaises(test_module.web.HTTPForbidden):
                await test_module.credential_exchange_issue(self.request)

    async def test_credential_exchange_issue_rev_reg_full(self):
        self.request.json = async_mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec, async_mock.patch.object(
            test_module, "CredentialManager", autospec=True
        ) as mock_credential_manager, async_mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex:

            mock_cred_ex.retrieve_by_id = async_mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.return_value.state = (
                mock_cred_ex.STATE_REQUEST_RECEIVED
            )

            mock_conn_rec.retrieve_by_id = async_mock.CoroutineMock()
            mock_conn_rec.retrieve_by_id.return_value.is_ready = True

            mock_issue_cred = async_mock.CoroutineMock(
                side_effect=test_module.IndyIssuerError()
            )
            mock_credential_manager.return_value.issue_credential = mock_issue_cred

            with self.assertRaises(test_module.web.HTTPBadRequest) as context:
                await test_module.credential_exchange_issue(self.request)

    async def test_credential_exchange_issue_deser_x(self):
        self.request.json = async_mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        mock_cred_ex_rec = async_mock.MagicMock(
            connection_id="dummy",
            serialize=async_mock.MagicMock(side_effect=test_module.BaseModelError()),
        )
        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec, async_mock.patch.object(
            test_module, "CredentialManager", autospec=True
        ) as mock_credential_manager, async_mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex:
            mock_cred_ex.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_cred_ex_rec
            )
            mock_credential_manager.return_value.issue_credential.return_value = (
                mock_cred_ex_rec,
                async_mock.MagicMock(),
            )
            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_issue(self.request)

    async def test_credential_exchange_store(self):
        self.request.json = async_mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec, async_mock.patch.object(
            test_module, "CredentialManager", autospec=True
        ) as mock_credential_manager, async_mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:

            mock_cred_ex.retrieve_by_id = async_mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.return_value.state = (
                mock_cred_ex.STATE_CREDENTIAL_RECEIVED
            )

            mock_cred_ex_record = async_mock.MagicMock()

            mock_credential_manager.return_value.store_credential.return_value = (
                mock_cred_ex_record,
                async_mock.MagicMock(),
            )

            await test_module.credential_exchange_store(self.request)

            mock_response.assert_called_once_with(
                mock_cred_ex_record.serialize.return_value
            )

    async def test_credential_exchange_store_bad_cred_id_json(self):
        self.request.json = async_mock.CoroutineMock(
            side_effect=test_module.JSONDecodeError("Nope", "Nope", 0)
        )
        self.request.match_info = {"cred_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec, async_mock.patch.object(
            test_module, "CredentialManager", autospec=True
        ) as mock_credential_manager, async_mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:

            mock_cred_ex.retrieve_by_id = async_mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.return_value.state = (
                mock_cred_ex.STATE_CREDENTIAL_RECEIVED
            )

            mock_cred_ex_record = async_mock.MagicMock()

            mock_credential_manager.return_value.store_credential.return_value = (
                mock_cred_ex_record,
                async_mock.MagicMock(),
            )

            await test_module.credential_exchange_store(self.request)

            mock_response.assert_called_once_with(
                mock_cred_ex_record.serialize.return_value
            )

    async def test_credential_exchange_store_bad_cred_ex_id(self):
        self.request.json = async_mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex:
            mock_cred_ex.connection_id = "conn-123"
            mock_cred_ex.thread_id = "conn-123"
            mock_cred_ex.retrieve_by_id = async_mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.side_effect = test_module.StorageNotFoundError()

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.credential_exchange_store(self.request)

    async def test_credential_exchange_store_no_conn_record(self):
        self.request.json = async_mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec, async_mock.patch.object(
            test_module, "CredentialManager", autospec=True
        ) as mock_credential_manager, async_mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex:
            mock_cred_ex.connection_id = "conn-123"
            mock_cred_ex.thread_id = "conn-123"
            mock_cred_ex.retrieve_by_id = async_mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.return_value.state = (
                mock_cred_ex.STATE_CREDENTIAL_RECEIVED
            )

            # Emulate storage not found (bad connection id)
            mock_conn_rec.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=test_module.StorageNotFoundError()
            )

            mock_credential_manager.return_value.store_credential.return_value = (
                mock_cred_ex,
                async_mock.MagicMock(),
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_store(self.request)

    async def test_credential_exchange_store_not_ready(self):
        self.request.json = async_mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec, async_mock.patch.object(
            test_module, "CredentialManager", autospec=True
        ) as mock_credential_manager, async_mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex:
            mock_cred_ex.connection_id = "conn-123"
            mock_cred_ex.thread_id = "conn-123"
            mock_cred_ex.retrieve_by_id = async_mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.return_value.state = (
                mock_cred_ex.STATE_CREDENTIAL_RECEIVED
            )

            # Emulate connection not ready
            mock_conn_rec.retrieve_by_id = async_mock.CoroutineMock()
            mock_conn_rec.retrieve_by_id.return_value.is_ready = False

            mock_credential_manager.return_value.store_credential.return_value = (
                mock_cred_ex,
                async_mock.MagicMock(),
            )

            with self.assertRaises(test_module.web.HTTPForbidden):
                await test_module.credential_exchange_store(self.request)

    async def test_credential_exchange_remove(self):
        self.request.match_info = {"cred_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_cred_ex.retrieve_by_id = async_mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.return_value = mock_cred_ex

            mock_cred_ex.delete_record = async_mock.CoroutineMock()

            await test_module.credential_exchange_remove(self.request)

            mock_response.assert_called_once_with({})

    async def test_credential_exchange_remove_bad_cred_ex_id(self):
        mock = async_mock.MagicMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex:
            # Emulate storage not found (bad cred ex id)
            mock_cred_ex.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=test_module.StorageNotFoundError()
            )

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.credential_exchange_remove(self.request)

    async def test_credential_exchange_remove_x(self):
        mock = async_mock.MagicMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex:
            # Emulate storage not found (bad cred ex id)
            mock_rec = async_mock.MagicMock(
                delete_record=async_mock.CoroutineMock(
                    side_effect=test_module.StorageError()
                )
            )
            mock_cred_ex.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_rec
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_remove(self.request)

    async def test_credential_exchange_problem_report(self):
        self.request.json = async_mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec, async_mock.patch.object(
            test_module, "CredentialManager", autospec=True
        ) as mock_credential_manager, async_mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex, async_mock.patch.object(
            test_module, "ProblemReport", autospec=True
        ) as mock_prob_report, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:

            mock_cred_ex.retrieve_by_id = async_mock.CoroutineMock()

            await test_module.credential_exchange_problem_report(self.request)

            mock_response.assert_called_once_with({})
            self.request.app["outbound_message_router"].assert_awaited_once_with(
                mock_prob_report.return_value,
                connection_id=mock_cred_ex.retrieve_by_id.return_value.connection_id,
            )

    async def test_credential_exchange_problem_report_bad_cred_id(self):
        self.request.json = async_mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "V10CredentialExchange", autospec=True
        ) as mock_cred_ex:
            mock_cred_ex.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=test_module.StorageNotFoundError()
            )

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.credential_exchange_problem_report(self.request)

    async def test_register(self):
        mock_app = async_mock.MagicMock()
        mock_app.add_routes = async_mock.MagicMock()

        await test_module.register(mock_app)
        mock_app.add_routes.assert_called_once()

    async def test_post_process_routes(self):
        mock_app = async_mock.MagicMock(_state={"swagger_dict": {}})
        test_module.post_process_routes(mock_app)
        assert "tags" in mock_app._state["swagger_dict"]
