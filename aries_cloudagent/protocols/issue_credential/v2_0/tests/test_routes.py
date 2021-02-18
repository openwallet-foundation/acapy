from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from .....admin.request_context import AdminRequestContext
from .....wallet.base import BaseWallet, DIDInfo

from .. import routes as test_module

TEST_DID = "LjgpST2rjsoxYegQDRm7EL"


class TestV20CredRoutes(AsyncTestCase):
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

    async def test_validate_cred_filter(self):
        filt = test_module.V20CredFilter()
        filt.validate_fields({"indy": {"issuer_did": TEST_DID}})
        filt.validate_fields(
            {"indy": {"issuer_did": TEST_DID, "schema_version": "1.0"}}
        )
        filt.validate_fields(
            {
                "indy": {"issuer_did": TEST_DID},
                "dif": {"some_dif_criterion": "..."},
            }
        )
        filt.validate_fields(
            {
                "indy": {},
                "dif": {"some_dif_criterion": "..."},
            }
        )
        with self.assertRaises(test_module.ValidationError):
            filt.validate_fields({})
        with self.assertRaises(test_module.ValidationError):
            filt.validate_fields(["hopeless", "stop"])
        with self.assertRaises(test_module.ValidationError):
            filt.validate_fields({"veres-one": {"no": "support"}})

    async def test_credential_exchange_list(self):
        self.request.query = {
            "thread_id": "dummy",
            "connection_id": "dummy",
            "role": "dummy",
            "state": "dummy",
        }

        with async_mock.patch.object(
            test_module, "V20CredExRecord", autospec=True
        ) as mock_cx_rec, async_mock.patch.object(
            test_module, "V20CredManager", autospec=True
        ) as mock_cred_mgr:
            mock_cx_rec.query = async_mock.CoroutineMock(return_value=[mock_cx_rec])
            mock_cx_rec.serialize = async_mock.MagicMock(
                return_value={"hello": "world"}
            )

            mock_cred_mgr.return_value.get_detail_record = async_mock.CoroutineMock(
                return_value=None
            )

            with async_mock.patch.object(
                test_module.web, "json_response"
            ) as mock_response:
                await test_module.credential_exchange_list(self.request)
                mock_response.assert_called_once_with(
                    {
                        "results": [
                            {
                                "cred_ex_record": mock_cx_rec.serialize.return_value,
                                "indy": None,
                                "dif": None,
                            }
                        ]
                    }
                )

    async def test_credential_exchange_list_x(self):
        self.request.query = {
            "thread_id": "dummy",
            "connection_id": "dummy",
            "role": "dummy",
            "state": "dummy",
        }

        with async_mock.patch.object(
            test_module, "V20CredExRecord", autospec=True
        ) as mock_cx_rec:
            mock_cx_rec.conn_id = "conn-123"
            mock_cx_rec.thread_id = "conn-123"
            mock_cx_rec.query = async_mock.CoroutineMock(
                side_effect=test_module.StorageError()
            )
            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_list(self.request)

    async def test_credential_exchange_retrieve(self):
        self.request.match_info = {"cred_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "V20CredExRecord", autospec=True
        ) as mock_cx_rec, async_mock.patch.object(
            test_module, "V20CredManager", autospec=True
        ) as mock_cred_mgr:
            mock_cx_rec.conn_id = "conn-123"
            mock_cx_rec.thread_id = "conn-123"
            mock_cx_rec.retrieve_by_id = async_mock.CoroutineMock()
            mock_cx_rec.retrieve_by_id.return_value = mock_cx_rec
            mock_cx_rec.serialize = async_mock.MagicMock()
            mock_cx_rec.serialize.return_value = {"hello": "world"}

            mock_cred_mgr.return_value.get_detail_record = async_mock.CoroutineMock(
                side_effect=[
                    async_mock.MagicMock(  # indy
                        serialize=async_mock.MagicMock(return_value={"...": "..."})
                    ),
                    None,  # dif
                ]
            )

            with async_mock.patch.object(
                test_module.web, "json_response"
            ) as mock_response:
                await test_module.credential_exchange_retrieve(self.request)
                mock_response.assert_called_once_with(
                    {
                        "cred_ex_record": mock_cx_rec.serialize.return_value,
                        "indy": {"...": "..."},
                        "dif": None,
                    }
                )

    async def test_credential_exchange_retrieve_not_found(self):
        self.request.match_info = {"cred_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "V20CredExRecord", autospec=True
        ) as mock_cx_rec:
            mock_cx_rec.conn_id = "conn-123"
            mock_cx_rec.thread_id = "conn-123"
            mock_cx_rec.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=test_module.StorageNotFoundError()
            )
            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.credential_exchange_retrieve(self.request)

    async def test_credential_exchange_retrieve_x(self):
        self.request.match_info = {"cred_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "V20CredExRecord", autospec=True
        ) as mock_cx_rec, async_mock.patch.object(
            test_module, "V20CredManager", autospec=True
        ) as mock_cred_mgr:
            mock_cx_rec.conn_id = "conn-123"
            mock_cx_rec.thread_id = "conn-123"
            mock_cx_rec.retrieve_by_id = async_mock.CoroutineMock()
            mock_cx_rec.retrieve_by_id.return_value = mock_cx_rec
            mock_cx_rec.serialize = async_mock.MagicMock(
                side_effect=test_module.BaseModelError()
            )

            mock_cred_mgr.return_value.get_detail_record = async_mock.CoroutineMock(
                return_value=None
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_retrieve(self.request)

    async def test_credential_exchange_create(self):
        self.request.json = async_mock.CoroutineMock()

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "V20CredManager", autospec=True
        ) as mock_cred_mgr, async_mock.patch.object(
            test_module.V20CredPreview, "deserialize", autospec=True
        ) as mock_cred_preview_deser, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_cred_mgr.return_value.create_offer = async_mock.CoroutineMock()

            mock_cred_mgr.return_value.create_offer.return_value = (
                async_mock.CoroutineMock(),
                async_mock.CoroutineMock(),
            )

            mock_cx_rec = async_mock.MagicMock()
            mock_cred_offer = async_mock.MagicMock()

            mock_cred_mgr.return_value.prepare_send.return_value = (
                mock_cx_rec,
                mock_cred_offer,
            )

            await test_module.credential_exchange_create(self.request)

            mock_response.assert_called_once_with(mock_cx_rec.serialize.return_value)

    async def test_credential_exchange_create_x(self):
        self.request.json = async_mock.CoroutineMock()

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_connection_record, async_mock.patch.object(
            test_module, "V20CredManager", autospec=True
        ) as mock_cred_mgr, async_mock.patch.object(
            test_module.V20CredPreview, "deserialize", autospec=True
        ) as mock_cred_preview_deser, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_cred_mgr.return_value.create_offer = async_mock.CoroutineMock()

            mock_cred_mgr.return_value.create_offer.return_value = (
                async_mock.CoroutineMock(),
                async_mock.CoroutineMock(),
            )

            mock_cred_mgr.return_value.prepare_send.side_effect = (
                test_module.StorageError()
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_create(self.request)

    async def test_credential_exchange_create_no_preview(self):
        conn_id = "connection-id"

        self.request.json = async_mock.CoroutineMock(
            return_value={"connection_id": conn_id}
        )

        with self.assertRaises(test_module.web.HTTPBadRequest) as context:
            await test_module.credential_exchange_create(self.request)
        assert "credential_preview" in str(context.exception)

    async def test_credential_exchange_create_no_filter(self):
        conn_id = "connection-id"

        self.request.json = async_mock.CoroutineMock(
            return_value={
                "connection_id": conn_id,
                "credential_preview": {
                    "attributes": [{"name": "hello", "value": "world"}]
                },
            }
        )

        with self.assertRaises(test_module.web.HTTPBadRequest) as context:
            await test_module.credential_exchange_create(self.request)
        assert "Missing filter" in str(context.exception)

    async def test_credential_exchange_send(self):
        self.request.json = async_mock.CoroutineMock()

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec, async_mock.patch.object(
            test_module, "V20CredManager", autospec=True
        ) as mock_cred_mgr, async_mock.patch.object(
            test_module.V20CredPreview, "deserialize", autospec=True
        ) as mock_cred_preview_deser, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_cred_mgr.return_value.create_offer = async_mock.CoroutineMock()

            mock_cred_mgr.return_value.create_offer.return_value = (
                async_mock.CoroutineMock(),
                async_mock.CoroutineMock(),
            )

            mock_cx_rec = async_mock.MagicMock()
            mock_cred_offer = async_mock.MagicMock()

            mock_cred_mgr.return_value.prepare_send.return_value = (
                mock_cx_rec,
                mock_cred_offer,
            )

            await test_module.credential_exchange_send(self.request)

            mock_response.assert_called_once_with(mock_cx_rec.serialize.return_value)

    async def test_credential_exchange_send_no_proposal(self):
        conn_id = "connection-id"

        self.request.json = async_mock.CoroutineMock(
            return_value={"connection_id": conn_id}
        )

        with self.assertRaises(test_module.web.HTTPBadRequest) as context:
            await test_module.credential_exchange_send(self.request)
        assert "credential_preview" in str(context.exception)

    async def test_credential_exchange_send_no_conn_record(self):
        conn_id = "connection-id"
        preview_spec = {"attributes": [{"name": "attr", "value": "value"}]}

        self.request.json = async_mock.CoroutineMock(
            return_value={"connection_id": conn_id, "credential_preview": preview_spec}
        )

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec, async_mock.patch.object(
            test_module, "V20CredManager", autospec=True
        ) as mock_cred_mgr:

            # Emulate storage not found (bad connection id)
            mock_conn_rec.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=test_module.StorageNotFoundError()
            )

            mock_cred_mgr.return_value.create_offer.return_value = (
                async_mock.MagicMock(),
                async_mock.MagicMock(),
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_send(self.request)

    async def test_credential_exchange_send_not_ready(self):
        conn_id = "connection-id"
        preview_spec = {"attributes": [{"name": "attr", "value": "value"}]}

        self.request.json = async_mock.CoroutineMock(
            return_value={
                "connection_id": conn_id,
                "credential_preview": preview_spec,
                "filter": {"indy": {"schema_version": "1.0"}},
            }
        )

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec, async_mock.patch.object(
            test_module, "V20CredManager", autospec=True
        ) as mock_cred_mgr:
            mock_conn_rec.retrieve_by_id.return_value.is_ready = False

            mock_cred_mgr.return_value.create_offer.return_value = (
                async_mock.MagicMock(),
                async_mock.MagicMock(),
            )

            with self.assertRaises(test_module.web.HTTPForbidden):
                await test_module.credential_exchange_send(self.request)

    async def test_credential_exchange_send_x(self):
        self.request.json = async_mock.CoroutineMock()

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec, async_mock.patch.object(
            test_module, "V20CredManager", autospec=True
        ) as mock_cred_mgr, async_mock.patch.object(
            test_module.V20CredPreview, "deserialize", autospec=True
        ) as mock_cred_preview_deser:
            mock_cred_mgr.return_value.create_offer = async_mock.CoroutineMock()

            mock_cred_mgr.return_value.create_offer.return_value = (
                async_mock.CoroutineMock(),
                async_mock.CoroutineMock(),
            )

            mock_cred_mgr.return_value.prepare_send.side_effect = (
                test_module.StorageError()
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_send(self.request)

    async def test_credential_exchange_send_proposal(self):
        conn_id = "connection-id"
        preview_spec = {"attributes": [{"name": "attr", "value": "value"}]}

        self.request.json = async_mock.CoroutineMock(
            return_value={
                "connection_id": conn_id,
                "credential_preview": preview_spec,
                "filter": {"indy": {"schema_version": "1.0"}},
            }
        )

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec, async_mock.patch.object(
            test_module, "V20CredManager", autospec=True
        ) as mock_cred_mgr, async_mock.patch.object(
            test_module.V20CredProposal, "deserialize", autospec=True
        ) as mock_cred_proposal_deser, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_cx_rec = async_mock.MagicMock()
            mock_cred_mgr.return_value.create_proposal.return_value = mock_cx_rec

            await test_module.credential_exchange_send_proposal(self.request)

            mock_response.assert_called_once_with(mock_cx_rec.serialize.return_value)

            self.request["outbound_message_router"].assert_awaited_once_with(
                mock_cred_proposal_deser.return_value, connection_id=conn_id
            )

    async def test_credential_exchange_send_proposal_no_filter(self):
        conn_id = "connection-id"
        self.request.json = async_mock.CoroutineMock(
            return_value={
                "comment": "comment",
                "connection_id": conn_id,
            }
        )

        with self.assertRaises(test_module.web.HTTPBadRequest) as context:
            await test_module.credential_exchange_send_proposal(self.request)
        assert "Missing filter" in str(context.exception)

    async def test_credential_exchange_send_proposal_no_conn_record(self):
        self.request.json = async_mock.CoroutineMock()

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec, async_mock.patch.object(
            test_module, "V20CredManager", autospec=True
        ) as mock_cred_mgr, async_mock.patch.object(
            test_module.V20CredPreview, "deserialize", autospec=True
        ) as mock_preview_deser:
            # Emulate storage not found (bad connection id)
            mock_conn_rec.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=test_module.StorageNotFoundError()
            )

            mock_cred_mgr.return_value.create_proposal.return_value = (
                async_mock.MagicMock()
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_send_proposal(self.request)

    async def test_credential_exchange_send_proposal_deser_x(self):
        conn_id = "connection-id"
        preview_spec = {"attributes": [{"name": "attr", "value": "value"}]}

        self.request.json = async_mock.CoroutineMock(
            return_value={
                "connection_id": conn_id,
                "credential_preview": preview_spec,
                "filter": {"indy": {"schema_version": "1.0"}},
            }
        )

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec, async_mock.patch.object(
            test_module, "V20CredManager", autospec=True
        ) as mock_cred_mgr, async_mock.patch.object(
            test_module.V20CredProposal, "deserialize", autospec=True
        ) as mock_cred_proposal_deser:
            mock_cx_rec = async_mock.MagicMock()
            mock_cred_mgr.return_value.create_proposal.return_value = mock_cx_rec
            mock_cred_proposal_deser.side_effect = test_module.BaseModelError()
            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_send_proposal(self.request)

    async def test_credential_exchange_send_proposal_not_ready(self):
        self.request.json = async_mock.CoroutineMock()

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec, async_mock.patch.object(
            test_module, "V20CredManager", autospec=True
        ) as mock_cred_mgr, async_mock.patch.object(
            test_module.V20CredPreview, "deserialize", autospec=True
        ) as mock_preview_deser:

            # Emulate connection not ready
            mock_conn_rec.retrieve_by_id = async_mock.CoroutineMock()
            mock_conn_rec.retrieve_by_id.return_value.is_ready = False

            mock_cred_mgr.return_value.create_proposal.return_value = (
                async_mock.MagicMock()
            )

            with self.assertRaises(test_module.web.HTTPForbidden):
                await test_module.credential_exchange_send_proposal(self.request)

    async def test_credential_exchange_create_free_offer(self):
        self.request.json = async_mock.CoroutineMock(
            return_value={
                "auto_issue": False,
                "connection_id": "dummy",
                "credential_preview": {
                    "attributes": [{"name": "hello", "value": "world"}]
                },
                "filter": {"indy": {"schema_version": "1.0"}},
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
            test_module, "V20CredManager", autospec=True
        ) as mock_cred_mgr, async_mock.patch.object(
            test_module, "serialize_outofband"
        ) as mock_seroob, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_cred_mgr.return_value.create_offer = async_mock.CoroutineMock()
            mock_cx_rec = async_mock.MagicMock()
            mock_cred_mgr.return_value.create_offer.return_value = (
                mock_cx_rec,
                async_mock.MagicMock(),
            )
            mock_seroob.return_value = "abc123"

            await test_module.credential_exchange_create_free_offer(self.request)

            mock_response.assert_called_once_with(
                {
                    "record": mock_cx_rec.serialize.return_value,
                    "oob_url": "abc123",
                }
            )

    async def test_credential_exchange_create_free_offer_no_filter(self):
        self.request.json = async_mock.CoroutineMock(
            return_value={
                "auto_issue": False,
                "connection_id": "dummy",
                "credential_preview": {
                    "attributes": [{"name": "hello", "value": "world"}]
                },
            }
        )

        with self.assertRaises(test_module.web.HTTPBadRequest) as context:
            await test_module.credential_exchange_create_free_offer(self.request)
        assert "Missing filter" in str(context.exception)

    async def test_credential_exchange_create_free_offer_no_preview(self):
        self.request.json = async_mock.CoroutineMock(
            return_value={
                "comment": "comment",
                "filter": {"indy": {"schema_version": "1.0"}},
            }
        )

        with self.assertRaises(test_module.web.HTTPBadRequest) as context:
            await test_module.credential_exchange_create_free_offer(self.request)
        assert "Missing credential_preview" in str(context.exception)

    async def test_credential_exchange_create_free_offer_retrieve_conn_rec_x(self):
        self.request.json = async_mock.CoroutineMock(
            return_value={
                "auto_issue": False,
                "connection_id": "dummy",
                "credential_preview": {
                    "attributes": [{"name": "hello", "value": "world"}]
                },
                "filter": {"indy": {"schema_version": "1.0"}},
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
                "credential_preview": {
                    "attributes": [{"name": "hello", "value": "world"}]
                },
                "filter": {"indy": {"schema_version": "1.0"}},
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
            test_module, "V20CredManager", autospec=True
        ) as mock_cred_mgr, async_mock.patch.object(
            test_module, "serialize_outofband"
        ) as mock_seroob, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:

            mock_cred_mgr.return_value.create_offer = async_mock.CoroutineMock()

            mock_cx_rec = async_mock.MagicMock()

            mock_cred_mgr.return_value.create_offer.return_value = (
                mock_cx_rec,
                async_mock.MagicMock(),
            )

            mock_seroob.return_value = "abc123"

            await test_module.credential_exchange_create_free_offer(self.request)

            mock_response.assert_called_once_with(
                {
                    "record": mock_cx_rec.serialize.return_value,
                    "oob_url": "abc123",
                }
            )

    async def test_credential_exchange_create_free_offer_no_conn_id_no_public_did(self):
        self.request.json = async_mock.CoroutineMock(
            return_value={
                "auto_issue": False,
                "credential_preview": {
                    "attributes": [{"name": "hello", "value": "world"}]
                },
                "filter": {"indy": {"schema_version": "1.0"}},
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
                "credential_preview": {
                    "attributes": [{"name": "hello", "value": "world"}]
                },
                "filter": {"indy": {"schema_version": "1.0"}},
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
                "connection_id": "dummy",
                "credential_preview": {
                    "attributes": [{"name": "hello", "value": "world"}]
                },
                "filter": {"indy": {"schema_version": "1.0"}},
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
            test_module, "V20CredManager", autospec=True
        ) as mock_cred_mgr:
            mock_cred_mgr.return_value.create_offer = async_mock.CoroutineMock()
            mock_cred_mgr.return_value.create_offer.side_effect = (
                test_module.BaseModelError()
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_create_free_offer(self.request)

    async def test_credential_exchange_send_free_offer(self):
        self.request.json = async_mock.CoroutineMock(
            return_value={
                "auto_issue": False,
                "credential_preview": {
                    "attributes": [{"name": "hello", "value": "world"}]
                },
                "filter": {"indy": {"schema_version": "1.0"}},
            }
        )

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec, async_mock.patch.object(
            test_module, "V20CredManager", autospec=True
        ) as mock_cred_mgr, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:

            mock_cred_mgr.return_value.create_offer = async_mock.CoroutineMock()

            mock_cx_rec = async_mock.MagicMock()

            mock_cred_mgr.return_value.create_offer.return_value = (
                mock_cx_rec,
                async_mock.MagicMock(),
            )

            await test_module.credential_exchange_send_free_offer(self.request)

            mock_response.assert_called_once_with(mock_cx_rec.serialize.return_value)

    async def test_credential_exchange_send_free_offer_no_filter(self):
        self.request.json = async_mock.CoroutineMock(
            return_value={
                "comment": "comment",
                "credential_preview": {
                    "attributes": [{"name": "hello", "value": "world"}]
                },
            }
        )

        with self.assertRaises(test_module.web.HTTPBadRequest) as context:
            await test_module.credential_exchange_send_free_offer(self.request)
        assert "Missing filter" in str(context.exception)

    async def test_credential_exchange_send_free_offer_no_preview(self):
        self.request.json = async_mock.CoroutineMock(
            return_value={
                "filter": {"indy": {"schema_version": "1.0"}},
            }
        )

        with self.assertRaises(test_module.web.HTTPBadRequest) as context:
            await test_module.credential_exchange_send_free_offer(self.request)
        assert "Missing credential_preview" in str(context.exception)

    async def test_credential_exchange_send_free_offer_no_conn_record(self):
        self.request.json = async_mock.CoroutineMock(
            return_value={
                "auto_issue": False,
                "credential_preview": {
                    "attributes": [{"name": "hello", "value": "world"}]
                },
                "filter": {"indy": {"schema_version": "1.0"}},
            }
        )

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec, async_mock.patch.object(
            test_module, "V20CredManager", autospec=True
        ) as mock_cred_mgr:

            # Emulate storage not found (bad connection id)
            mock_conn_rec.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=test_module.StorageNotFoundError()
            )

            mock_cred_mgr.return_value.create_offer = async_mock.CoroutineMock()
            mock_cred_mgr.return_value.create_offer.return_value = (
                async_mock.MagicMock(),
                async_mock.MagicMock(),
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_send_free_offer(self.request)

    async def test_credential_exchange_send_free_offer_not_ready(self):
        self.request.json = async_mock.CoroutineMock(
            return_value={
                "auto_issue": True,
                "credential_preview": {
                    "attributes": [{"name": "hello", "value": "world"}]
                },
                "filter": {"indy": {"schema_version": "1.0"}},
            }
        )

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec, async_mock.patch.object(
            test_module, "V20CredManager", autospec=True
        ) as mock_cred_mgr:

            # Emulate connection not ready
            mock_conn_rec.retrieve_by_id = async_mock.CoroutineMock()
            mock_conn_rec.retrieve_by_id.return_value.is_ready = False

            mock_cred_mgr.return_value.create_offer = async_mock.CoroutineMock()
            mock_cred_mgr.return_value.create_offer.return_value = (
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
            test_module, "V20CredManager", autospec=True
        ) as mock_cred_mgr, async_mock.patch.object(
            test_module, "V20CredExRecord", autospec=True
        ) as mock_cls_cx_rec, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:

            mock_cls_cx_rec.retrieve_by_id = async_mock.CoroutineMock()
            mock_cls_cx_rec.retrieve_by_id.return_value.state = (
                test_module.V20CredExRecord.STATE_PROPOSAL_RECEIVED
            )

            mock_cred_mgr.return_value.create_offer = async_mock.CoroutineMock()

            mock_cx_rec = async_mock.MagicMock()

            mock_cred_mgr.return_value.create_offer.return_value = (
                mock_cx_rec,
                async_mock.MagicMock(),
            )

            await test_module.credential_exchange_send_bound_offer(self.request)

            mock_response.assert_called_once_with(mock_cx_rec.serialize.return_value)

    async def test_credential_exchange_send_bound_offer_bad_cred_ex_id(self):
        self.request.json = async_mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "V20CredExRecord", autospec=True
        ) as mock_cx_rec:
            mock_cx_rec.conn_id = "conn-123"
            mock_cx_rec.thread_id = "conn-123"
            mock_cx_rec.retrieve_by_id = async_mock.CoroutineMock()
            mock_cx_rec.retrieve_by_id.side_effect = test_module.StorageNotFoundError()

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.credential_exchange_send_bound_offer(self.request)

    async def test_credential_exchange_send_bound_offer_no_conn_record(self):
        self.request.json = async_mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec, async_mock.patch.object(
            test_module, "V20CredManager", autospec=True
        ) as mock_cred_mgr, async_mock.patch.object(
            test_module, "V20CredExRecord", autospec=True
        ) as mock_cx_rec:
            mock_cx_rec.conn_id = "conn-123"
            mock_cx_rec.thread_id = "conn-123"
            mock_cx_rec.retrieve_by_id = async_mock.CoroutineMock()
            mock_cx_rec.retrieve_by_id.return_value.state = (
                test_module.V20CredExRecord.STATE_PROPOSAL_RECEIVED
            )

            # Emulate storage not found (bad connection id)
            mock_conn_rec.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=test_module.StorageNotFoundError()
            )

            mock_cred_mgr.return_value.create_offer = async_mock.CoroutineMock()
            mock_cred_mgr.return_value.create_offer.return_value = (
                async_mock.MagicMock(),
                async_mock.MagicMock(),
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_send_bound_offer(self.request)

    async def test_credential_exchange_send_bound_offer_bad_state(self):
        self.request.json = async_mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "V20CredExRecord", autospec=True
        ) as mock_cx_rec:
            mock_cx_rec.conn_id = "conn-123"
            mock_cx_rec.thread_id = "conn-123"
            mock_cx_rec.retrieve_by_id = async_mock.CoroutineMock()
            mock_cx_rec.retrieve_by_id.return_value.state = (
                test_module.V20CredExRecord.STATE_DONE
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_send_bound_offer(self.request)

    async def test_credential_exchange_send_bound_offer_not_ready(self):
        self.request.json = async_mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec, async_mock.patch.object(
            test_module, "V20CredManager", autospec=True
        ) as mock_cred_mgr, async_mock.patch.object(
            test_module, "V20CredExRecord", autospec=True
        ) as mock_cx_rec:
            mock_cx_rec.conn_id = "conn-123"
            mock_cx_rec.thread_id = "conn-123"
            mock_cx_rec.retrieve_by_id = async_mock.CoroutineMock()
            mock_cx_rec.retrieve_by_id.return_value.state = (
                test_module.V20CredExRecord.STATE_PROPOSAL_RECEIVED
            )

            # Emulate connection not ready
            mock_conn_rec.retrieve_by_id = async_mock.CoroutineMock()
            mock_conn_rec.retrieve_by_id.return_value.is_ready = False

            mock_cred_mgr.return_value.create_offer = async_mock.CoroutineMock()
            mock_cred_mgr.return_value.create_offer.return_value = (
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
            test_module, "V20CredManager", autospec=True
        ) as mock_cred_mgr, async_mock.patch.object(
            test_module, "V20CredExRecord", autospec=True
        ) as mock_cls_cx_rec, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:

            mock_cls_cx_rec.retrieve_by_id = async_mock.CoroutineMock()
            mock_cls_cx_rec.retrieve_by_id.return_value.state = (
                test_module.V20CredExRecord.STATE_OFFER_RECEIVED
            )

            mock_cx_rec = async_mock.MagicMock()

            mock_cred_mgr.return_value.create_request.return_value = (
                mock_cx_rec,
                async_mock.MagicMock(),
            )

            await test_module.credential_exchange_send_request(self.request)

            mock_response.assert_called_once_with(mock_cx_rec.serialize.return_value)

    async def test_credential_exchange_send_request_bad_cred_ex_id(self):
        self.request.json = async_mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "V20CredExRecord", autospec=True
        ) as mock_cx_rec:
            mock_cx_rec.conn_id = "conn-123"
            mock_cx_rec.thread_id = "conn-123"
            mock_cx_rec.retrieve_by_id = async_mock.CoroutineMock()
            mock_cx_rec.retrieve_by_id.side_effect = test_module.StorageNotFoundError()

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.credential_exchange_send_request(self.request)

    async def test_credential_exchange_send_request_no_conn_record(self):
        self.request.json = async_mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec, async_mock.patch.object(
            test_module, "V20CredManager", autospec=True
        ) as mock_cred_mgr, async_mock.patch.object(
            test_module, "V20CredExRecord", autospec=True
        ) as mock_cx_rec:
            mock_cx_rec.conn_id = "conn-123"
            mock_cx_rec.thread_id = "conn-123"
            mock_cx_rec.retrieve_by_id = async_mock.CoroutineMock()
            mock_cx_rec.retrieve_by_id.return_value.state = (
                test_module.V20CredExRecord.STATE_OFFER_RECEIVED
            )

            # Emulate storage not found (bad connection id)
            mock_conn_rec.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=test_module.StorageNotFoundError()
            )

            mock_cred_mgr.return_value.create_offer = async_mock.CoroutineMock()
            mock_cred_mgr.return_value.create_offer.return_value = (
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
            test_module, "V20CredManager", autospec=True
        ) as mock_cred_mgr, async_mock.patch.object(
            test_module, "V20CredExRecord", autospec=True
        ) as mock_cx_rec:
            mock_cx_rec.conn_id = "conn-123"
            mock_cx_rec.thread_id = "conn-123"
            mock_cx_rec.retrieve_by_id = async_mock.CoroutineMock()
            mock_cx_rec.retrieve_by_id.return_value.state = (
                test_module.V20CredExRecord.STATE_OFFER_RECEIVED
            )

            # Emulate connection not ready
            mock_conn_rec.retrieve_by_id = async_mock.CoroutineMock()
            mock_conn_rec.retrieve_by_id.return_value.is_ready = False

            mock_cred_mgr.return_value.create_offer = async_mock.CoroutineMock()
            mock_cred_mgr.return_value.create_offer.return_value = (
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
            test_module, "V20CredManager", autospec=True
        ) as mock_cred_mgr, async_mock.patch.object(
            test_module, "V20CredExRecord", autospec=True
        ) as mock_cls_cx_rec, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_cls_cx_rec.retrieve_by_id = async_mock.CoroutineMock()
            mock_cls_cx_rec.retrieve_by_id.return_value.state = (
                test_module.V20CredExRecord.STATE_REQUEST_RECEIVED
            )
            mock_cx_rec = async_mock.MagicMock()

            mock_cred_mgr.return_value.get_detail_record = async_mock.CoroutineMock(
                side_effect=[
                    async_mock.MagicMock(  # indy
                        serialize=async_mock.MagicMock(return_value={"...": "..."})
                    ),
                    None,  # dif
                ]
            )

            mock_cred_mgr.return_value.issue_credential.return_value = (
                mock_cx_rec,
                async_mock.MagicMock(),
            )

            await test_module.credential_exchange_issue(self.request)

            mock_response.assert_called_once_with(
                {
                    "cred_ex_record": mock_cx_rec.serialize.return_value,
                    "indy": {"...": "..."},
                    "dif": None,
                }
            )

    async def test_credential_exchange_issue_bad_cred_ex_id(self):
        self.request.json = async_mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "V20CredExRecord", autospec=True
        ) as mock_cx_rec:
            mock_cx_rec.conn_id = "conn-123"
            mock_cx_rec.thread_id = "conn-123"
            mock_cx_rec.retrieve_by_id = async_mock.CoroutineMock()
            mock_cx_rec.retrieve_by_id.side_effect = test_module.StorageNotFoundError()

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.credential_exchange_issue(self.request)

    async def test_credential_exchange_issue_no_conn_record(self):
        self.request.json = async_mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec, async_mock.patch.object(
            test_module, "V20CredManager", autospec=True
        ) as mock_cred_mgr, async_mock.patch.object(
            test_module, "V20CredExRecord", autospec=True
        ) as mock_cx_rec:

            mock_cx_rec.retrieve_by_id = async_mock.CoroutineMock()
            mock_cx_rec.retrieve_by_id.return_value.state = (
                test_module.V20CredExRecord.STATE_REQUEST_RECEIVED
            )

            # Emulate storage not found (bad connection id)
            mock_conn_rec.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=test_module.StorageNotFoundError()
            )

            mock_cred_mgr.return_value.issue_credential = async_mock.CoroutineMock()
            mock_cred_mgr.return_value.issue_credential.return_value = (
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
            test_module, "V20CredManager", autospec=True
        ) as mock_cred_mgr, async_mock.patch.object(
            test_module, "V20CredExRecord", autospec=True
        ) as mock_cx_rec:

            mock_cx_rec.retrieve_by_id = async_mock.CoroutineMock()
            mock_cx_rec.retrieve_by_id.return_value.state = (
                test_module.V20CredExRecord.STATE_REQUEST_RECEIVED
            )

            # Emulate connection not ready
            mock_conn_rec.retrieve_by_id = async_mock.CoroutineMock()
            mock_conn_rec.retrieve_by_id.return_value.is_ready = False

            mock_cred_mgr.return_value.issue_credential = async_mock.CoroutineMock()
            mock_cred_mgr.return_value.issue_credential.return_value = (
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
            test_module, "V20CredManager", autospec=True
        ) as mock_cred_mgr, async_mock.patch.object(
            test_module, "V20CredExRecord", autospec=True
        ) as mock_cx_rec:

            mock_cx_rec.retrieve_by_id = async_mock.CoroutineMock()
            mock_cx_rec.retrieve_by_id.return_value.state = (
                test_module.V20CredExRecord.STATE_REQUEST_RECEIVED
            )

            mock_conn_rec.retrieve_by_id = async_mock.CoroutineMock()
            mock_conn_rec.retrieve_by_id.return_value.is_ready = True

            mock_issue_cred = async_mock.CoroutineMock(
                side_effect=test_module.IndyIssuerError()
            )
            mock_cred_mgr.return_value.issue_credential = mock_issue_cred

            with self.assertRaises(test_module.web.HTTPBadRequest) as context:
                await test_module.credential_exchange_issue(self.request)

    async def test_credential_exchange_issue_deser_x(self):
        self.request.json = async_mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        mock_cx_rec = async_mock.MagicMock(
            conn_id="dummy",
            serialize=async_mock.MagicMock(side_effect=test_module.BaseModelError()),
        )
        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec, async_mock.patch.object(
            test_module, "V20CredManager", autospec=True
        ) as mock_cred_mgr, async_mock.patch.object(
            test_module, "V20CredExRecord", autospec=True
        ) as mock_cls_cx_rec:
            mock_cls_cx_rec.retrieve_by_id = async_mock.CoroutineMock(
                return_value=mock_cx_rec
            )
            mock_cred_mgr.return_value.issue_credential.return_value = (
                mock_cx_rec,
                async_mock.MagicMock(),
            )

            mock_cred_mgr.return_value.get_detail_record = async_mock.CoroutineMock(
                side_effect=[
                    async_mock.MagicMock(  # indy
                        serialize=async_mock.MagicMock(return_value={"...": "..."})
                    ),
                    None,  # dif
                ]
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_issue(self.request)

    async def test_credential_exchange_store(self):
        self.request.json = async_mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec, async_mock.patch.object(
            test_module, "V20CredManager", autospec=True
        ) as mock_cred_mgr, async_mock.patch.object(
            test_module, "V20CredExRecord", autospec=True
        ) as mock_cls_cx_rec, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:

            mock_cls_cx_rec.retrieve_by_id = async_mock.CoroutineMock()
            mock_cls_cx_rec.retrieve_by_id.return_value.state = (
                test_module.V20CredExRecord.STATE_CREDENTIAL_RECEIVED
            )

            mock_cred_mgr.return_value.get_detail_record = async_mock.CoroutineMock(
                side_effect=[
                    async_mock.MagicMock(  # indy
                        serialize=async_mock.MagicMock(return_value={"...": "..."})
                    ),
                    None,  # dif
                ]
            )

            mock_cx_rec = async_mock.MagicMock()

            mock_cred_mgr.return_value.store_credential.return_value = (
                mock_cx_rec,
                async_mock.MagicMock(),
            )

            await test_module.credential_exchange_store(self.request)

            mock_response.assert_called_once_with(
                {
                    "cred_ex_record": mock_cx_rec.serialize.return_value,
                    "indy": {"...": "..."},
                    "dif": None,
                }
            )

    async def test_credential_exchange_store_bad_cred_id_json(self):
        self.request.json = async_mock.CoroutineMock(
            side_effect=test_module.JSONDecodeError("Nope", "Nope", 0)
        )
        self.request.match_info = {"cred_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec, async_mock.patch.object(
            test_module, "V20CredManager", autospec=True
        ) as mock_cred_mgr, async_mock.patch.object(
            test_module, "V20CredExRecord", autospec=True
        ) as mock_cls_cx_rec, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:

            mock_cls_cx_rec.retrieve_by_id = async_mock.CoroutineMock()
            mock_cls_cx_rec.retrieve_by_id.return_value.state = (
                test_module.V20CredExRecord.STATE_CREDENTIAL_RECEIVED
            )

            mock_cx_rec = async_mock.MagicMock()

            mock_cred_mgr.return_value.get_detail_record = async_mock.CoroutineMock(
                side_effect=[
                    async_mock.MagicMock(  # indy
                        serialize=async_mock.MagicMock(return_value={"...": "..."})
                    ),
                    None,  # dif
                ]
            )

            mock_cred_mgr.return_value.store_credential.return_value = (
                mock_cx_rec,
                async_mock.MagicMock(),
            )

            await test_module.credential_exchange_store(self.request)

            mock_response.assert_called_once_with(
                {
                    "cred_ex_record": mock_cx_rec.serialize.return_value,
                    "indy": {"...": "..."},
                    "dif": None,
                }
            )

    async def test_credential_exchange_store_bad_cred_ex_id(self):
        self.request.json = async_mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "V20CredExRecord", autospec=True
        ) as mock_cx_rec:
            mock_cx_rec.conn_id = "conn-123"
            mock_cx_rec.thread_id = "conn-123"
            mock_cx_rec.retrieve_by_id = async_mock.CoroutineMock()
            mock_cx_rec.retrieve_by_id.side_effect = test_module.StorageNotFoundError()

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.credential_exchange_store(self.request)

    async def test_credential_exchange_store_no_conn_record(self):
        self.request.json = async_mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec, async_mock.patch.object(
            test_module, "V20CredManager", autospec=True
        ) as mock_cred_mgr, async_mock.patch.object(
            test_module, "V20CredExRecord", autospec=True
        ) as mock_cx_rec:
            mock_cx_rec.conn_id = "conn-123"
            mock_cx_rec.thread_id = "conn-123"
            mock_cx_rec.retrieve_by_id = async_mock.CoroutineMock()
            mock_cx_rec.retrieve_by_id.return_value.state = (
                test_module.V20CredExRecord.STATE_CREDENTIAL_RECEIVED
            )

            # Emulate storage not found (bad connection id)
            mock_conn_rec.retrieve_by_id = async_mock.CoroutineMock(
                side_effect=test_module.StorageNotFoundError()
            )

            mock_cred_mgr.return_value.store_credential.return_value = (
                mock_cx_rec,
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
            test_module, "V20CredManager", autospec=True
        ) as mock_cred_mgr, async_mock.patch.object(
            test_module, "V20CredExRecord", autospec=True
        ) as mock_cx_rec:
            mock_cx_rec.conn_id = "conn-123"
            mock_cx_rec.thread_id = "conn-123"
            mock_cx_rec.retrieve_by_id = async_mock.CoroutineMock()
            mock_cx_rec.retrieve_by_id.return_value.state = (
                test_module.V20CredExRecord.STATE_CREDENTIAL_RECEIVED
            )

            # Emulate connection not ready
            mock_conn_rec.retrieve_by_id = async_mock.CoroutineMock()
            mock_conn_rec.retrieve_by_id.return_value.is_ready = False

            mock_cred_mgr.return_value.store_credential.return_value = (
                mock_cx_rec,
                async_mock.MagicMock(),
            )

            with self.assertRaises(test_module.web.HTTPForbidden):
                await test_module.credential_exchange_store(self.request)

    async def test_credential_exchange_remove(self):
        self.request.match_info = {"cred_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "V20CredManager", autospec=True
        ) as mock_cred_mgr, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_cred_mgr.return_value = async_mock.MagicMock(
                delete_cred_ex_record=async_mock.CoroutineMock()
            )
            await test_module.credential_exchange_remove(self.request)

            mock_response.assert_called_once_with({})

    async def test_credential_exchange_remove_bad_cred_ex_id(self):
        self.request.match_info = {"cred_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "V20CredManager", autospec=True
        ) as mock_cred_mgr:
            mock_cred_mgr.return_value = async_mock.MagicMock(
                delete_cred_ex_record=async_mock.CoroutineMock(
                    side_effect=test_module.StorageNotFoundError()
                )
            )

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.credential_exchange_remove(self.request)

    async def test_credential_exchange_remove_x(self):
        self.request.match_info = {"cred_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "V20CredManager", autospec=True
        ) as mock_cred_mgr:
            mock_cred_mgr.return_value = async_mock.MagicMock(
                delete_cred_ex_record=async_mock.CoroutineMock(
                    side_effect=test_module.StorageError()
                )
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_remove(self.request)

    async def test_credential_exchange_problem_report(self):
        self.request.json = async_mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "ConnRecord", autospec=True
        ) as mock_conn_rec, async_mock.patch.object(
            test_module, "V20CredExRecord", autospec=True
        ) as mock_cx_rec, async_mock.patch.object(
            test_module, "ProblemReport", autospec=True
        ) as mock_prob_report, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:

            mock_cx_rec.retrieve_by_id = async_mock.CoroutineMock()

            await test_module.credential_exchange_problem_report(self.request)

            mock_response.assert_called_once_with({})
            self.request["outbound_message_router"].assert_awaited_once_with(
                mock_prob_report.return_value,
                connection_id=mock_cx_rec.retrieve_by_id.return_value.conn_id,
            )

    async def test_credential_exchange_problem_report_bad_cred_id(self):
        self.request.json = async_mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with async_mock.patch.object(
            test_module, "V20CredExRecord", autospec=True
        ) as mock_cx_rec:
            mock_cx_rec.retrieve_by_id = async_mock.CoroutineMock(
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
