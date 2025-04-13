from unittest import IsolatedAsyncioTestCase

from .....admin.request_context import AdminRequestContext
from .....connections.models.conn_record import ConnRecord
from .....protocols.issue_credential.v2_0.models.cred_ex_record import V20CredExRecord
from .....tests import mock
from .....utils.testing import create_test_profile
from .....vc.ld_proofs.error import LinkedDataProofException
from .. import routes as test_module
from ..formats.indy.handler import IndyCredFormatHandler
from ..formats.ld_proof.handler import LDProofCredFormatHandler
from ..messages.cred_format import V20CredFormat
from . import LD_PROOF_VC_DETAIL, TEST_DID


class TestV20CredRoutes(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.session_inject = {}
        self.profile = await create_test_profile(
            settings={
                "admin.admin_api_key": "secret-key",
            }
        )
        self.context = AdminRequestContext.test_context(self.session_inject, self.profile)
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

    async def test_validate_cred_filter_schema(self):
        schema = test_module.V20CredFilterSchema()
        schema.validate_fields({"indy": {"issuer_did": TEST_DID}})
        schema.validate_fields(
            {"indy": {"issuer_did": TEST_DID, "schema_version": "1.0"}}
        )
        schema.validate_fields(
            {
                "indy": {"issuer_did": TEST_DID},
                "ld_proof": {"credential": {}, "options": {}},
            }
        )
        schema.validate_fields(
            {
                "indy": {},
                "ld_proof": {"credential": {}, "options": {}},
            }
        )
        with self.assertRaises(test_module.ValidationError):
            schema.validate_fields({})
        with self.assertRaises(test_module.ValidationError):
            schema.validate_fields(["hopeless", "stop"])
        with self.assertRaises(test_module.ValidationError):
            schema.validate_fields({"veres-one": {"no": "support"}})

    async def test_validate_cred_filter_anoncreds_schema(self):
        schema = test_module.V20CredFilterSchema()
        schema.validate_fields({"anoncreds": {"issuer_id": TEST_DID}})
        schema.validate_fields(
            {"anoncreds": {"issuer_id": TEST_DID, "schema_version": "1.0"}}
        )
        schema.validate_fields(
            {
                "anoncreds": {"issuer_id": TEST_DID},
            }
        )
        schema.validate_fields(
            {
                "anoncreds": {},
            }
        )
        with self.assertRaises(test_module.ValidationError):
            schema.validate_fields({})
        with self.assertRaises(test_module.ValidationError):
            schema.validate_fields(["hopeless", "stop"])
        with self.assertRaises(test_module.ValidationError):
            schema.validate_fields({"veres-one": {"no": "support"}})

    async def test_validate_create_schema(self):
        schema = test_module.V20IssueCredSchemaCore()
        schema.validate(
            {
                "filter": {"indy": {"issuer_did": TEST_DID}},
                "credential_preview": {"..": ".."},
            }
        )
        schema.validate({"filter": {"ld_proof": {"..": ".."}}})

        with self.assertRaises(test_module.ValidationError):
            schema.validate({"filter": {"indy": {"..": ".."}}})

    async def test_validate_bound_offer_request_schema(self):
        schema = test_module.V20CredBoundOfferRequestSchema()
        schema.validate_fields({})
        schema.validate_fields(
            {"filter_": {"indy": {"issuer_did": TEST_DID}}, "counter_preview": {}}
        )
        schema.validate_fields(
            {"filter_": {"ld_proof": {"issuer_did": TEST_DID}}, "counter_preview": {}}
        )
        with self.assertRaises(test_module.ValidationError):
            schema.validate_fields({"filter_": {"indy": {"issuer_did": TEST_DID}}})
            schema.validate_fields({"filter_": {"ld_proof": {"issuer_did": TEST_DID}}})
            schema.validate_fields({"counter_preview": {}})

    async def test_credential_exchange_list(self):
        self.request.query = {
            "thread_id": "dummy",
            "connection_id": "dummy",
            "role": "dummy",
            "state": "dummy",
        }

        with mock.patch.object(
            test_module, "V20CredExRecord", autospec=True
        ) as mock_cx_rec:
            mock_cx_rec.query = mock.CoroutineMock(
                return_value=[
                    V20CredExRecord(
                        connection_id="conn-123",
                        by_format=V20CredFormat.Format.INDY,
                        thread_id="conn-123",
                        cred_ex_id="dummy",
                    )
                ]
            )
            mock_cx_rec.serialize = mock.MagicMock(return_value={"hello": "world"})

            with mock.patch.object(test_module.web, "json_response") as mock_response:
                await test_module.credential_exchange_list(self.request)
                mock_response.assert_called()

    async def test_credential_exchange_list_x(self):
        self.request.query = {
            "thread_id": "dummy",
            "connection_id": "dummy",
            "role": "dummy",
            "state": "dummy",
        }

        with mock.patch.object(
            test_module, "V20CredExRecord", autospec=True
        ) as mock_cx_rec:
            mock_cx_rec.connection_id = "conn-123"
            mock_cx_rec.thread_id = "conn-123"
            mock_cx_rec.query = mock.CoroutineMock(side_effect=test_module.StorageError())
            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_list(self.request)

    async def test_credential_exchange_retrieve(self):
        self.request.match_info = {"cred_ex_id": "dummy"}

        with (
            mock.patch.object(
                test_module, "V20CredExRecord", autospec=True
            ) as mock_cx_rec,
            mock.patch.object(V20CredFormat.Format, "handler") as mock_handler,
        ):
            mock_cx_rec.connection_id = "conn-123"
            mock_cx_rec.thread_id = "conn-123"
            mock_cx_rec.retrieve_by_id = mock.CoroutineMock()
            mock_cx_rec.retrieve_by_id.return_value = mock_cx_rec
            mock_cx_rec.serialize = mock.MagicMock()
            mock_cx_rec.serialize.return_value = {"hello": "world"}

            mock_handler.return_value.get_detail_record = mock.CoroutineMock(
                side_effect=[
                    mock.MagicMock(  # anoncreds
                        serialize=mock.MagicMock(return_value={"...": "..."})
                    ),
                    None,  # indy
                    None,  # ld_proof
                    None,  # vc_di
                ]
            )

            with mock.patch.object(test_module.web, "json_response") as mock_response:
                await test_module.credential_exchange_retrieve(self.request)
                mock_response.assert_called_once_with(
                    {
                        "cred_ex_record": mock_cx_rec.serialize.return_value,
                        "anoncreds": {"...": "..."},
                        "indy": None,
                        "ld_proof": None,
                        "vc_di": None,
                    }
                )

    async def test_credential_exchange_retrieve_indy_ld_proof(self):
        self.request.match_info = {"cred_ex_id": "dummy"}

        with (
            mock.patch.object(
                test_module, "V20CredExRecord", autospec=True
            ) as mock_cx_rec,
            mock.patch.object(V20CredFormat.Format, "handler") as mock_handler,
        ):
            mock_cx_rec.connection_id = "conn-123"
            mock_cx_rec.thread_id = "conn-123"
            mock_cx_rec.retrieve_by_id = mock.CoroutineMock()
            mock_cx_rec.retrieve_by_id.return_value = mock_cx_rec
            mock_cx_rec.serialize = mock.MagicMock()
            mock_cx_rec.serialize.return_value = {"hello": "world"}

            mock_handler.return_value.get_detail_record = mock.CoroutineMock(
                side_effect=[
                    mock.MagicMock(  # anoncreds
                        serialize=mock.MagicMock(return_value={"anon": "creds"})
                    ),
                    mock.MagicMock(  # indy
                        serialize=mock.MagicMock(return_value={"in": "dy"})
                    ),
                    mock.MagicMock(  # ld_proof
                        serialize=mock.MagicMock(return_value={"ld": "proof"})
                    ),
                    mock.MagicMock(  # vc_di
                        serialize=mock.MagicMock(return_value={"vc": "di"})
                    ),
                ]
            )

            with mock.patch.object(test_module.web, "json_response") as mock_response:
                await test_module.credential_exchange_retrieve(self.request)
                mock_response.assert_called_once_with(
                    {
                        "cred_ex_record": mock_cx_rec.serialize.return_value,
                        "anoncreds": {"anon": "creds"},
                        "indy": {"in": "dy"},
                        "ld_proof": {"ld": "proof"},
                        "vc_di": {"vc": "di"},
                    }
                )

    async def test_credential_exchange_retrieve_not_found(self):
        self.request.match_info = {"cred_ex_id": "dummy"}

        with mock.patch.object(
            test_module, "V20CredExRecord", autospec=True
        ) as mock_cx_rec:
            mock_cx_rec.connection_id = "conn-123"
            mock_cx_rec.thread_id = "conn-123"
            mock_cx_rec.retrieve_by_id = mock.CoroutineMock(
                side_effect=test_module.StorageNotFoundError()
            )
            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.credential_exchange_retrieve(self.request)

    async def test_credential_exchange_retrieve_x(self):
        self.request.match_info = {"cred_ex_id": "dummy"}

        with (
            mock.patch.object(
                test_module, "V20CredExRecord", autospec=True
            ) as mock_cx_rec,
            mock.patch.object(V20CredFormat.Format, "handler") as mock_handler,
        ):
            mock_cx_rec.connection_id = "conn-123"
            mock_cx_rec.thread_id = "conn-123"
            mock_cx_rec.retrieve_by_id = mock.CoroutineMock()
            mock_cx_rec.retrieve_by_id.return_value = mock_cx_rec
            mock_cx_rec.serialize = mock.MagicMock(
                side_effect=test_module.BaseModelError()
            )

            mock_handler.return_value.get_detail_record = mock.CoroutineMock(
                return_value=None
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_retrieve(self.request)

    async def test_credential_exchange_create(self):
        self.request.json = mock.CoroutineMock()

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True),
            mock.patch.object(
                test_module, "V20CredManager", autospec=True
            ) as mock_cred_mgr,
            mock.patch.object(test_module.V20CredPreview, "deserialize", autospec=True),
            mock.patch.object(test_module.web, "json_response") as mock_response,
        ):
            mock_cred_mgr.return_value.create_offer = mock.CoroutineMock()

            mock_cred_mgr.return_value.create_offer.return_value = (
                mock.CoroutineMock(),
                mock.CoroutineMock(),
            )

            mock_cx_rec = mock.MagicMock()
            mock_cred_offer = mock.MagicMock()

            mock_cred_mgr.return_value.prepare_send.return_value = (
                mock_cx_rec,
                mock_cred_offer,
            )

            await test_module.credential_exchange_create(self.request)

            mock_response.assert_called_once_with(mock_cx_rec.serialize.return_value)

    async def test_credential_exchange_create_x(self):
        self.request.json = mock.CoroutineMock()

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True),
            mock.patch.object(
                test_module, "V20CredManager", autospec=True
            ) as mock_cred_mgr,
            mock.patch.object(test_module.V20CredPreview, "deserialize", autospec=True),
            mock.patch.object(test_module.web, "json_response"),
        ):
            mock_cred_mgr.return_value.create_offer = mock.CoroutineMock()

            mock_cred_mgr.return_value.create_offer.return_value = (
                mock.CoroutineMock(),
                mock.CoroutineMock(),
            )

            mock_cred_mgr.return_value.prepare_send.side_effect = (
                test_module.StorageError()
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_create(self.request)

    async def test_credential_exchange_create_no_filter(self):
        connection_id = "connection-id"

        self.request.json = mock.CoroutineMock(
            return_value={
                "connection_id": connection_id,
                "credential_preview": {
                    "attributes": [{"name": "hello", "value": "world"}]
                },
            }
        )

        with self.assertRaises(test_module.web.HTTPBadRequest) as context:
            await test_module.credential_exchange_create(self.request)
        assert "Missing filter" in str(context.exception)

    async def test_credential_exchange_send(self):
        self.request.json = mock.CoroutineMock()

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True),
            mock.patch.object(
                test_module, "V20CredManager", autospec=True
            ) as mock_cred_mgr,
            mock.patch.object(test_module.V20CredPreview, "deserialize", autospec=True),
            mock.patch.object(test_module.web, "json_response") as mock_response,
        ):
            mock_cred_mgr.return_value.create_offer = mock.CoroutineMock()

            mock_cred_mgr.return_value.create_offer.return_value = (
                mock.CoroutineMock(),
                mock.CoroutineMock(),
            )

            mock_cx_rec = mock.MagicMock()
            mock_cred_offer = mock.MagicMock()

            mock_cred_mgr.return_value.prepare_send.return_value = (
                mock_cx_rec,
                mock_cred_offer,
            )

            await test_module.credential_exchange_send(self.request)

            mock_response.assert_called_once_with(mock_cx_rec.serialize.return_value)

    async def test_credential_exchange_send_request_no_conn_no_holder_did(self):
        self.request.json = mock.CoroutineMock(return_value={})
        self.request.match_info = {"cred_ex_id": "dummy"}

        with (
            mock.patch.object(test_module, "OobRecord", autospec=True) as mock_oob_rec,
            mock.patch.object(
                test_module, "default_did_from_verkey", autospec=True
            ) as mock_default_did_from_verkey,
            mock.patch.object(
                test_module, "V20CredManager", autospec=True
            ) as mock_cred_mgr,
            mock.patch.object(
                test_module, "V20CredExRecord", autospec=True
            ) as mock_cred_ex,
            mock.patch.object(test_module.web, "json_response") as mock_response,
        ):
            mock_oob_rec.retrieve_by_tag_filter = mock.CoroutineMock(
                return_value=mock.MagicMock(our_recipient_key="our-recipient_key")
            )
            mock_default_did_from_verkey.return_value = "holder-did"

            mock_cred_ex.retrieve_by_id = mock.CoroutineMock()
            mock_cred_ex.retrieve_by_id.return_value.state = (
                mock_cred_ex.STATE_OFFER_RECEIVED
            )
            mock_cred_ex.retrieve_by_id.return_value.connection_id = None

            mock_cred_ex_record = mock.MagicMock()

            mock_cred_mgr.return_value.create_request.return_value = (
                mock_cred_ex_record,
                mock.MagicMock(),
            )

            await test_module.credential_exchange_send_bound_request(self.request)

            mock_cred_mgr.return_value.create_request.assert_called_once_with(
                mock_cred_ex.retrieve_by_id.return_value, "holder-did"
            )
            mock_response.assert_called_once_with(
                mock_cred_ex_record.serialize.return_value
            )
            mock_default_did_from_verkey.assert_called_once_with("our-recipient_key")

    async def test_credential_exchange_send_no_conn_record(self):
        connection_id = "connection-id"
        preview_spec = {"attributes": [{"name": "attr", "value": "value"}]}

        self.request.json = mock.CoroutineMock(
            return_value={
                "connection_id": connection_id,
                "credential_preview": preview_spec,
            }
        )

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True) as mock_conn_rec,
            mock.patch.object(
                test_module, "V20CredManager", autospec=True
            ) as mock_cred_mgr,
        ):
            # Emulate storage not found (bad connection id)
            mock_conn_rec.retrieve_by_id = mock.CoroutineMock(
                side_effect=test_module.StorageNotFoundError()
            )

            mock_cred_mgr.return_value.create_offer.return_value = (
                mock.MagicMock(),
                mock.MagicMock(),
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_send(self.request)

    async def test_credential_exchange_send_not_ready(self):
        connection_id = "connection-id"
        preview_spec = {"attributes": [{"name": "attr", "value": "value"}]}

        self.request.json = mock.CoroutineMock(
            return_value={
                "connection_id": connection_id,
                "credential_preview": preview_spec,
                "filter": {"indy": {"schema_version": "1.0"}},
            }
        )

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True) as mock_conn_rec,
            mock.patch.object(
                test_module, "V20CredManager", autospec=True
            ) as mock_cred_mgr,
        ):
            mock_conn_rec.retrieve_by_id.return_value.is_ready = False

            mock_cred_mgr.return_value.create_offer.return_value = (
                mock.MagicMock(),
                mock.MagicMock(),
            )

            with self.assertRaises(test_module.web.HTTPForbidden):
                await test_module.credential_exchange_send(self.request)

    async def test_credential_exchange_send_x(self):
        self.request.json = mock.CoroutineMock()

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True),
            mock.patch.object(
                test_module, "V20CredManager", autospec=True
            ) as mock_cred_mgr,
            mock.patch.object(test_module.V20CredPreview, "deserialize", autospec=True),
        ):
            mock_cred_ex_record = mock.MagicMock(
                serialize=mock.MagicMock(side_effect=test_module.BaseModelError()),
                save_error_state=mock.CoroutineMock(),
            )
            mock_cred_offer = mock.MagicMock()
            mock_cred_mgr.return_value = mock.CoroutineMock(
                create_offer=mock.CoroutineMock(
                    return_value=(
                        mock.CoroutineMock(),
                        mock.CoroutineMock(),
                    )
                ),
                prepare_send=mock.CoroutineMock(
                    return_value=(
                        mock_cred_ex_record,
                        mock_cred_offer,
                    )
                ),
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_send(self.request)

    async def test_credential_exchange_send_proposal(self):
        connection_id = "connection-id"
        preview_spec = {"attributes": [{"name": "attr", "value": "value"}]}

        self.request.json = mock.CoroutineMock(
            return_value={
                "connection_id": connection_id,
                "credential_preview": preview_spec,
                "filter": {"indy": {"schema_version": "1.0"}},
            }
        )

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True),
            mock.patch.object(
                test_module, "V20CredManager", autospec=True
            ) as mock_cred_mgr,
            mock.patch.object(test_module.web, "json_response") as mock_response,
        ):
            mock_cx_rec = mock.MagicMock()
            mock_cred_mgr.return_value.create_proposal.return_value = mock_cx_rec

            await test_module.credential_exchange_send_proposal(self.request)

            mock_response.assert_called_once_with(mock_cx_rec.serialize.return_value)

            self.request["outbound_message_router"].assert_awaited_once()

    async def test_credential_exchange_send_proposal_no_filter(self):
        connection_id = "connection-id"
        self.request.json = mock.CoroutineMock(
            return_value={
                "comment": "comment",
                "connection_id": connection_id,
            }
        )

        with self.assertRaises(test_module.web.HTTPBadRequest) as context:
            await test_module.credential_exchange_send_proposal(self.request)
        assert "Missing filter" in str(context.exception)

    async def test_credential_exchange_send_proposal_no_conn_record(self):
        self.request.json = mock.CoroutineMock()

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True) as mock_conn_rec,
            mock.patch.object(
                test_module, "V20CredManager", autospec=True
            ) as mock_cred_mgr,
            mock.patch.object(test_module.V20CredPreview, "deserialize", autospec=True),
        ):
            # Emulate storage not found (bad connection id)
            mock_conn_rec.retrieve_by_id = mock.CoroutineMock(
                side_effect=test_module.StorageNotFoundError()
            )

            mock_cred_mgr.return_value.create_proposal.return_value = mock.MagicMock()

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_send_proposal(self.request)

    async def test_credential_exchange_send_proposal_x(self):
        connection_id = "connection-id"
        preview_spec = {"attributes": [{"name": "attr", "value": "value"}]}

        self.request.json = mock.CoroutineMock(
            return_value={
                "connection_id": connection_id,
                "credential_preview": preview_spec,
                "filter": {"indy": {"schema_version": "1.0"}},
            }
        )

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True),
            mock.patch.object(
                test_module, "V20CredManager", autospec=True
            ) as mock_cred_mgr,
        ):
            mock_cx_rec = mock.MagicMock(
                serialize=mock.MagicMock(side_effect=test_module.BaseModelError()),
                save_error_state=mock.CoroutineMock(),
            )
            mock_cred_mgr.return_value.create_proposal.return_value = mock_cx_rec

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_send_proposal(self.request)

    async def test_credential_exchange_send_proposal_not_ready(self):
        self.request.json = mock.CoroutineMock()

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True) as mock_conn_rec,
            mock.patch.object(
                test_module, "V20CredManager", autospec=True
            ) as mock_cred_mgr,
            mock.patch.object(test_module.V20CredPreview, "deserialize", autospec=True),
        ):
            # Emulate connection not ready
            mock_conn_rec.retrieve_by_id = mock.CoroutineMock()
            mock_conn_rec.retrieve_by_id.return_value.is_ready = False

            mock_cred_mgr.return_value.create_proposal.return_value = mock.MagicMock()

            with self.assertRaises(test_module.web.HTTPForbidden):
                await test_module.credential_exchange_send_proposal(self.request)

    async def test_credential_exchange_create_free_offer(self):
        self.request.json = mock.CoroutineMock(
            return_value={
                "auto_issue": False,
                "credential_preview": {
                    "attributes": [{"name": "hello", "value": "world"}]
                },
                "filter": {"indy": {"schema_version": "1.0"}},
            }
        )

        self.context.update_settings({"debug.auto_respond_credential_offer": True})
        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True),
            mock.patch.object(
                test_module, "V20CredManager", autospec=True
            ) as mock_cred_mgr,
            mock.patch.object(test_module.web, "json_response") as mock_response,
        ):
            mock_cred_mgr.return_value.create_offer = mock.CoroutineMock()
            mock_cx_rec = mock.MagicMock()
            mock_cred_mgr.return_value.create_offer.return_value = (
                mock_cx_rec,
                mock.MagicMock(),
            )

            await test_module.credential_exchange_create_free_offer(self.request)

            mock_response.assert_called_once_with(mock_cx_rec.serialize.return_value)

    async def test_credential_exchange_create_free_offer_no_filter(self):
        self.request.json = mock.CoroutineMock(
            return_value={
                "auto_issue": False,
                "credential_preview": {
                    "attributes": [{"name": "hello", "value": "world"}]
                },
            }
        )

        with self.assertRaises(test_module.web.HTTPBadRequest) as context:
            await test_module.credential_exchange_create_free_offer(self.request)
        assert "Missing filter" in str(context.exception)

    async def test_credential_exchange_create_free_offer_x(self):
        self.request.json = mock.CoroutineMock(
            return_value={
                "auto_issue": False,
                "credential_preview": {
                    "attributes": [{"name": "hello", "value": "world"}]
                },
                "filter": {"indy": {"schema_version": "1.0"}},
            }
        )

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True),
            mock.patch.object(
                test_module, "V20CredManager", autospec=True
            ) as mock_cred_mgr,
        ):
            mock_cx_rec = mock.MagicMock(
                serialize=mock.MagicMock(
                    side_effect=test_module.BaseModelError(),
                ),
                save_error_state=mock.CoroutineMock(),
            )
            mock_cred_mgr.return_value = mock.MagicMock(
                create_offer=mock.CoroutineMock(
                    return_value=(
                        mock_cx_rec,
                        mock.MagicMock(),
                    )
                )
            )
            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_create_free_offer(self.request)

    async def test_credential_exchange_send_free_offer(self):
        self.request.json = mock.CoroutineMock(
            return_value={
                "auto_issue": False,
                "credential_preview": {
                    "attributes": [{"name": "hello", "value": "world"}]
                },
                "filter": {"indy": {"schema_version": "1.0"}},
            }
        )

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True),
            mock.patch.object(
                test_module, "V20CredManager", autospec=True
            ) as mock_cred_mgr,
            mock.patch.object(test_module.web, "json_response") as mock_response,
        ):
            mock_cred_mgr.return_value.create_offer = mock.CoroutineMock()
            mock_cx_rec = mock.MagicMock()
            mock_cred_mgr.return_value.create_offer.return_value = (
                mock_cx_rec,
                mock.MagicMock(),
            )

            await test_module.credential_exchange_send_free_offer(self.request)
            mock_response.assert_called_once_with(mock_cx_rec.serialize.return_value)

    async def test_credential_exchange_send_free_offer_vcdi(self):
        self.request.json = mock.CoroutineMock(
            return_value={
                "filter": {"vc_di": {"schema_version": "1.0"}},
                "comment": "This is a test comment.",
                "auto_issue": True,
                "auto-remove": True,
                "replacement_id": "test_replacement_id",
                "credential_preview": {
                    "@type": "https://didcomm.org/issue-credential/2.0/credential-preview",
                    "attributes": [
                        {"name": "name", "value": "Alice Smith"},
                        {"name": "date", "value": "2018-05-28"},
                        {"name": "degree", "value": "Maths"},
                        {"name": "birthdate_dateint", "value": "20000330"},
                        {"name": "timestamp", "value": "1711836271"},
                    ],
                },
            }
        )

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True),
            mock.patch.object(
                test_module, "V20CredManager", autospec=True
            ) as mock_cred_mgr,
            mock.patch.object(test_module.web, "json_response") as mock_response,
        ):
            # Mock the creation of a credential offer, especially for handling VC-DI
            mock_cred_mgr.return_value.create_offer = mock.CoroutineMock()
            mock_cx_rec = mock.MagicMock()
            mock_cred_mgr.return_value.create_offer.return_value = (
                mock_cx_rec,
                mock.MagicMock(),
            )

            # Call the function you are testing
            await test_module.credential_exchange_send_free_offer(self.request)

            # Validate that the response is correctly structured and called once
            mock_response.assert_called_once_with(mock_cx_rec.serialize.return_value)

    async def test_credential_exchange_send_free_offer_no_filter(self):
        self.request.json = mock.CoroutineMock(
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

    async def test_credential_exchange_send_free_offer_no_conn_record(self):
        self.request.json = mock.CoroutineMock(
            return_value={
                "auto_issue": False,
                "credential_preview": {
                    "attributes": [{"name": "hello", "value": "world"}]
                },
                "filter": {"indy": {"schema_version": "1.0"}},
            }
        )

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True) as mock_conn_rec,
            mock.patch.object(
                test_module, "V20CredManager", autospec=True
            ) as mock_cred_mgr,
        ):
            # Emulate storage not found (bad connection id)
            mock_conn_rec.retrieve_by_id = mock.CoroutineMock(
                side_effect=test_module.StorageNotFoundError()
            )

            mock_cred_mgr.return_value.create_offer = mock.CoroutineMock()
            mock_cred_mgr.return_value.create_offer.return_value = (
                mock.MagicMock(),
                mock.MagicMock(),
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_send_free_offer(self.request)

    async def test_credential_exchange_send_free_offer_not_ready(self):
        self.request.json = mock.CoroutineMock(
            return_value={
                "auto_issue": True,
                "credential_preview": {
                    "attributes": [{"name": "hello", "value": "world"}]
                },
                "filter": {"indy": {"schema_version": "1.0"}},
            }
        )

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True) as mock_conn_rec,
            mock.patch.object(
                test_module, "V20CredManager", autospec=True
            ) as mock_cred_mgr,
        ):
            # Emulate connection not ready
            mock_conn_rec.retrieve_by_id = mock.CoroutineMock()
            mock_conn_rec.retrieve_by_id.return_value.is_ready = False

            mock_cred_mgr.return_value.create_offer = mock.CoroutineMock()
            mock_cred_mgr.return_value.create_offer.return_value = (
                mock.MagicMock(),
                mock.MagicMock(),
            )

            with self.assertRaises(test_module.web.HTTPForbidden):
                await test_module.credential_exchange_send_free_offer(self.request)

    async def test_credential_exchange_send_free_offer_x(self):
        self.request.json = mock.CoroutineMock(
            return_value={
                "auto_issue": False,
                "credential_preview": {
                    "attributes": [{"name": "hello", "value": "world"}]
                },
                "filter": {"indy": {"schema_version": "1.0"}},
            }
        )

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True),
            mock.patch.object(
                test_module, "V20CredManager", autospec=True
            ) as mock_cred_mgr,
            mock.patch.object(test_module.web, "json_response"),
        ):
            mock_cx_rec = mock.MagicMock(
                serialize=mock.MagicMock(side_effect=test_module.BaseModelError()),
                save_error_state=mock.CoroutineMock(),
            )
            mock_cred_mgr.return_value = mock.CoroutineMock(
                create_offer=mock.CoroutineMock(
                    return_value=(
                        mock_cx_rec,
                        mock.MagicMock(),
                    )
                )
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_send_free_offer(self.request)

    async def test_credential_exchange_send_bound_offer(self):
        self.request.json = mock.CoroutineMock(return_value={})
        self.request.match_info = {"cred_ex_id": "dummy"}

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True),
            mock.patch.object(
                test_module, "V20CredManager", autospec=True
            ) as mock_cred_mgr,
            mock.patch.object(
                test_module, "V20CredExRecord", autospec=True
            ) as mock_cx_rec_cls,
            mock.patch.object(test_module.web, "json_response") as mock_response,
        ):
            mock_cx_rec_cls.retrieve_by_id = mock.CoroutineMock()
            mock_cx_rec_cls.retrieve_by_id.return_value.state = (
                test_module.V20CredExRecord.STATE_PROPOSAL_RECEIVED
            )

            mock_cred_mgr.return_value.create_offer = mock.CoroutineMock()

            mock_cx_rec = mock.MagicMock()

            mock_cred_mgr.return_value.create_offer.return_value = (
                mock_cx_rec,
                mock.MagicMock(),
            )

            await test_module.credential_exchange_send_bound_offer(self.request)

            mock_response.assert_called_once_with(mock_cx_rec.serialize.return_value)

    async def test_credential_exchange_send_bound_offer_linked_data_error(self):
        self.request.json = mock.CoroutineMock(return_value={})
        self.request.match_info = {"cred_ex_id": "dummy"}

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True),
            mock.patch.object(
                test_module, "V20CredManager", autospec=True
            ) as mock_cred_mgr,
            mock.patch.object(
                test_module, "V20CredExRecord", autospec=True
            ) as mock_cx_rec_cls,
            mock.patch.object(test_module.web, "json_response"),
        ):
            mock_cx_rec_cls.retrieve_by_id = mock.CoroutineMock()
            mock_cx_rec_cls.retrieve_by_id.return_value.state = (
                test_module.V20CredExRecord.STATE_PROPOSAL_RECEIVED
            )

            mock_cred_mgr.return_value.create_offer = mock.CoroutineMock()

            exception_message = "ex"
            mock_cred_mgr.return_value.create_offer.side_effect = (
                LinkedDataProofException(exception_message)
            )
            with self.assertRaises(test_module.web.HTTPBadRequest) as error:
                await test_module.credential_exchange_send_bound_offer(self.request)

            assert exception_message in str(error.exception)

    async def test_credential_exchange_send_bound_offer_bad_cred_ex_id(self):
        self.request.json = mock.CoroutineMock(return_value={})
        self.request.match_info = {"cred_ex_id": "dummy"}

        with mock.patch.object(
            test_module, "V20CredExRecord", autospec=True
        ) as mock_cx_rec:
            mock_cx_rec.connection_id = "conn-123"
            mock_cx_rec.thread_id = "conn-123"
            mock_cx_rec.retrieve_by_id = mock.CoroutineMock()
            mock_cx_rec.retrieve_by_id.side_effect = test_module.StorageNotFoundError()

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.credential_exchange_send_bound_offer(self.request)

    async def test_credential_exchange_send_bound_offer_no_conn_record(self):
        self.request.json = mock.CoroutineMock(return_value={})
        self.request.match_info = {"cred_ex_id": "dummy"}

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True) as mock_conn_rec,
            mock.patch.object(
                test_module, "V20CredManager", autospec=True
            ) as mock_cred_mgr,
            mock.patch.object(
                test_module, "V20CredExRecord", autospec=True
            ) as mock_cx_rec,
        ):
            mock_cx_rec.connection_id = "conn-123"
            mock_cx_rec.thread_id = "conn-123"
            mock_cx_rec.retrieve_by_id = mock.CoroutineMock(
                return_value=mock.MagicMock(
                    state=mock_cx_rec.STATE_PROPOSAL_RECEIVED,
                    save_error_state=mock.CoroutineMock(),
                )
            )

            # Emulate storage not found (bad connection id)
            mock_conn_rec.retrieve_by_id = mock.CoroutineMock(
                side_effect=test_module.StorageNotFoundError()
            )

            mock_cred_mgr.return_value.create_offer = mock.CoroutineMock()
            mock_cred_mgr.return_value.create_offer.return_value = (
                mock.MagicMock(),
                mock.MagicMock(),
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_send_bound_offer(self.request)

    async def test_credential_exchange_send_bound_offer_bad_state(self):
        self.request.json = mock.CoroutineMock(return_value={})
        self.request.match_info = {"cred_ex_id": "dummy"}

        with mock.patch.object(
            test_module, "V20CredExRecord", autospec=True
        ) as mock_cx_rec:
            mock_cx_rec.connection_id = "conn-123"
            mock_cx_rec.thread_id = "conn-123"
            mock_cx_rec.retrieve_by_id = mock.CoroutineMock(
                return_value=mock.MagicMock(
                    state=mock_cx_rec.STATE_DONE,
                    save_error_state=mock.CoroutineMock(),
                )
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_send_bound_offer(self.request)

    async def test_credential_exchange_send_bound_offer_not_ready(self):
        self.request.json = mock.CoroutineMock(return_value={})
        self.request.match_info = {"cred_ex_id": "dummy"}

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True) as mock_conn_rec,
            mock.patch.object(
                test_module, "V20CredManager", autospec=True
            ) as mock_cred_mgr,
            mock.patch.object(
                test_module, "V20CredExRecord", autospec=True
            ) as mock_cx_rec,
        ):
            mock_cx_rec.connection_id = "conn-123"
            mock_cx_rec.thread_id = "conn-123"
            mock_cx_rec.retrieve_by_id = mock.CoroutineMock()
            mock_cx_rec.retrieve_by_id.return_value.state = (
                test_module.V20CredExRecord.STATE_PROPOSAL_RECEIVED
            )

            # Emulate connection not ready
            mock_conn_rec.retrieve_by_id = mock.CoroutineMock()
            mock_conn_rec.retrieve_by_id.return_value.is_ready = False

            mock_cred_mgr.return_value.create_offer = mock.CoroutineMock()
            mock_cred_mgr.return_value.create_offer.return_value = (
                mock.MagicMock(),
                mock.MagicMock(),
            )

            with self.assertRaises(test_module.web.HTTPForbidden):
                await test_module.credential_exchange_send_bound_offer(self.request)

    async def test_credential_exchange_send_request(self):
        self.request.json = mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True),
            mock.patch.object(
                test_module, "V20CredManager", autospec=True
            ) as mock_cred_mgr,
            mock.patch.object(
                test_module, "V20CredExRecord", autospec=True
            ) as mock_cx_rec_cls,
            mock.patch.object(test_module.web, "json_response") as mock_response,
        ):
            mock_cx_rec_cls.retrieve_by_id = mock.CoroutineMock()
            mock_cx_rec_cls.retrieve_by_id.return_value.state = (
                test_module.V20CredExRecord.STATE_OFFER_RECEIVED
            )

            mock_cx_rec = mock.MagicMock()

            mock_cred_mgr.return_value.create_request.return_value = (
                mock_cx_rec,
                mock.MagicMock(),
            )

            await test_module.credential_exchange_send_bound_request(self.request)

            mock_response.assert_called_once_with(mock_cx_rec.serialize.return_value)

    async def test_credential_exchange_send_request_bad_cred_ex_id(self):
        self.request.json = mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with mock.patch.object(
            test_module, "V20CredExRecord", autospec=True
        ) as mock_cx_rec:
            mock_cx_rec.connection_id = "conn-123"
            mock_cx_rec.thread_id = "conn-123"
            mock_cx_rec.retrieve_by_id = mock.CoroutineMock()
            mock_cx_rec.retrieve_by_id.side_effect = test_module.StorageNotFoundError()

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.credential_exchange_send_bound_request(self.request)

    async def test_credential_exchange_send_request_no_conn_record(self):
        self.request.json = mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True) as mock_conn_rec,
            mock.patch.object(
                test_module, "V20CredManager", autospec=True
            ) as mock_cred_mgr,
            mock.patch.object(
                test_module, "V20CredExRecord", autospec=True
            ) as mock_cx_rec,
        ):
            mock_cx_rec.connection_id = "conn-123"
            mock_cx_rec.thread_id = "conn-123"
            mock_cx_rec.retrieve_by_id = mock.CoroutineMock()
            mock_cx_rec.retrieve_by_id.return_value = mock.MagicMock(
                state=mock_cx_rec.STATE_OFFER_RECEIVED,
                save_error_state=mock.CoroutineMock(),
            )

            # Emulate storage not found (bad connection id)
            mock_conn_rec.retrieve_by_id = mock.CoroutineMock(
                side_effect=test_module.StorageNotFoundError()
            )

            mock_cred_mgr.return_value.create_offer = mock.CoroutineMock()
            mock_cred_mgr.return_value.create_offer.return_value = (
                mock.MagicMock(),
                mock.MagicMock(),
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_send_bound_request(self.request)

    async def test_credential_exchange_send_request_not_ready(self):
        self.request.json = mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True) as mock_conn_rec,
            mock.patch.object(
                test_module, "V20CredManager", autospec=True
            ) as mock_cred_mgr,
            mock.patch.object(
                test_module, "V20CredExRecord", autospec=True
            ) as mock_cx_rec,
        ):
            mock_cx_rec.connection_id = "conn-123"
            mock_cx_rec.thread_id = "conn-123"
            mock_cx_rec.retrieve_by_id = mock.CoroutineMock()
            mock_cx_rec.retrieve_by_id.return_value.state = (
                test_module.V20CredExRecord.STATE_OFFER_RECEIVED
            )

            # Emulate connection not ready
            mock_conn_rec.retrieve_by_id = mock.CoroutineMock()
            mock_conn_rec.retrieve_by_id.return_value.is_ready = False

            mock_cred_mgr.return_value.create_offer = mock.CoroutineMock()
            mock_cred_mgr.return_value.create_offer.return_value = (
                mock.MagicMock(),
                mock.MagicMock(),
            )

            with self.assertRaises(test_module.web.HTTPForbidden):
                await test_module.credential_exchange_send_bound_request(self.request)

    async def test_credential_exchange_send_free_request(self):
        self.request.json = mock.CoroutineMock(
            return_value={
                "filter": {"ld_proof": LD_PROOF_VC_DETAIL},
            }
        )

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True),
            mock.patch.object(
                test_module, "V20CredManager", autospec=True
            ) as mock_cred_mgr,
            mock.patch.object(test_module.web, "json_response") as mock_response,
        ):
            mock_cred_mgr.return_value.create_request = mock.CoroutineMock()

            mock_cx_rec = mock.MagicMock()

            mock_cred_mgr.return_value.create_request.return_value = (
                mock_cx_rec,
                mock.MagicMock(),
            )

            await test_module.credential_exchange_send_free_request(self.request)

            mock_response.assert_called_once_with(mock_cx_rec.serialize.return_value)

    async def test_credential_exchange_send_free_request_no_filter(self):
        self.request.json = mock.CoroutineMock(return_value={"comment": "comment"})

        with self.assertRaises(test_module.web.HTTPBadRequest) as context:
            await test_module.credential_exchange_send_free_request(self.request)
        assert "Missing filter" in str(context.exception)

    async def test_credential_exchange_send_free_request_no_conn_record(self):
        self.request.json = mock.CoroutineMock(
            return_value={
                "filter": {"ld_proof": LD_PROOF_VC_DETAIL},
            }
        )

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True) as mock_conn_rec,
            mock.patch.object(
                test_module, "V20CredManager", autospec=True
            ) as mock_cred_mgr,
        ):
            # Emulate storage not found (bad connection id)
            mock_conn_rec.retrieve_by_id = mock.CoroutineMock(
                side_effect=test_module.StorageNotFoundError()
            )

            mock_cred_mgr.return_value.create_request = mock.CoroutineMock()
            mock_cred_mgr.return_value.create_request.return_value = (
                mock.MagicMock(),
                mock.MagicMock(),
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_send_free_request(self.request)

    async def test_credential_exchange_send_free_request_not_ready(self):
        self.request.json = mock.CoroutineMock(
            return_value={
                "filter": {"ld_proof": LD_PROOF_VC_DETAIL},
            }
        )

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True) as mock_conn_rec,
            mock.patch.object(
                test_module, "V20CredManager", autospec=True
            ) as mock_cred_mgr,
        ):
            # Emulate connection not ready
            mock_conn_rec.retrieve_by_id = mock.CoroutineMock()
            mock_conn_rec.retrieve_by_id.return_value.is_ready = False

            mock_cred_mgr.return_value.create_request = mock.CoroutineMock()
            mock_cred_mgr.return_value.create_request.return_value = (
                mock.MagicMock(),
                mock.MagicMock(),
            )

            with self.assertRaises(test_module.web.HTTPForbidden):
                await test_module.credential_exchange_send_free_request(self.request)

    async def test_credential_exchange_send_free_request_x(self):
        self.request.json = mock.CoroutineMock(
            return_value={
                "filter": {"ld_proof": LD_PROOF_VC_DETAIL},
            }
        )

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True),
            mock.patch.object(
                test_module, "V20CredManager", autospec=True
            ) as mock_cred_mgr,
            mock.patch.object(test_module.web, "json_response"),
        ):
            mock_cred_mgr.return_value.create_request = mock.CoroutineMock(
                side_effect=[
                    test_module.LedgerError(),
                    test_module.StorageError(),
                ]
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):  # ledger error
                await test_module.credential_exchange_send_free_request(self.request)
            with self.assertRaises(test_module.web.HTTPBadRequest):  # storage error
                await test_module.credential_exchange_send_free_request(self.request)

    async def test_credential_exchange_issue(self):
        self.request.json = mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True),
            mock.patch.object(
                test_module, "V20CredManager", autospec=True
            ) as mock_cred_mgr,
            mock.patch.object(
                test_module, "V20CredExRecord", autospec=True
            ) as mock_cx_rec_cls,
            mock.patch.object(test_module.web, "json_response") as mock_response,
            mock.patch.object(V20CredFormat.Format, "handler") as mock_handler,
        ):
            mock_cx_rec_cls.retrieve_by_id = mock.CoroutineMock()
            mock_cx_rec_cls.retrieve_by_id.return_value.state = (
                test_module.V20CredExRecord.STATE_REQUEST_RECEIVED
            )
            mock_cx_rec = mock.MagicMock()

            mock_handler.return_value.get_detail_record = mock.CoroutineMock(
                side_effect=[
                    mock.MagicMock(  # anoncreds
                        serialize=mock.MagicMock(return_value={"...": "..."})
                    ),
                    None,
                    None,  # ld_proof
                    None,  # vc_di
                ]
            )

            mock_cred_mgr.return_value.issue_credential.return_value = (
                mock_cx_rec,
                mock.MagicMock(),
            )

            await test_module.credential_exchange_issue(self.request)

            mock_response.assert_called_once_with(
                {
                    "cred_ex_record": mock_cx_rec.serialize.return_value,
                    "anoncreds": {"...": "..."},
                    "indy": None,
                    "ld_proof": None,
                    "vc_di": None,
                }
            )

    async def test_credential_exchange_issue_vcdi(self):
        self.request.json = mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True),
            mock.patch.object(
                test_module, "V20CredManager", autospec=True
            ) as mock_cred_mgr,
            mock.patch.object(
                test_module, "V20CredExRecord", autospec=True
            ) as mock_cx_rec_cls,
            mock.patch.object(test_module.web, "json_response") as mock_response,
            mock.patch.object(V20CredFormat.Format, "handler") as mock_handler,
        ):
            mock_cx_rec_cls.retrieve_by_id = mock.CoroutineMock()
            mock_cx_rec_cls.retrieve_by_id.return_value.state = (
                test_module.V20CredExRecord.STATE_REQUEST_RECEIVED
            )
            mock_cx_rec = mock.MagicMock()

            mock_handler.return_value.get_detail_record = mock.CoroutineMock(
                side_effect=[
                    None,  # anoncreds
                    None,  # indy
                    None,  # ld_proof
                    mock.MagicMock(  # indy
                        serialize=mock.MagicMock(return_value={"...": "..."})
                    ),  # vc_di
                ]
            )

            mock_cred_mgr.return_value.issue_credential.return_value = (
                mock_cx_rec,
                mock.MagicMock(),
            )

            await test_module.credential_exchange_issue(self.request)

            mock_response.assert_called_once_with(
                {
                    "cred_ex_record": mock_cx_rec.serialize.return_value,
                    "anoncreds": None,
                    "indy": None,
                    "ld_proof": None,
                    "vc_di": {"...": "..."},
                }
            )

    async def test_credential_exchange_issue_bad_cred_ex_id(self):
        self.request.json = mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with mock.patch.object(
            test_module, "V20CredExRecord", autospec=True
        ) as mock_cx_rec:
            mock_cx_rec.connection_id = "conn-123"
            mock_cx_rec.thread_id = "conn-123"
            mock_cx_rec.retrieve_by_id = mock.CoroutineMock()
            mock_cx_rec.retrieve_by_id.side_effect = test_module.StorageNotFoundError()

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.credential_exchange_issue(self.request)

    async def test_credential_exchange_issue_no_conn_record(self):
        self.request.json = mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        mock_cx_rec = mock.MagicMock(
            conn_id="dummy",
            serialize=mock.MagicMock(),
            save_error_state=mock.CoroutineMock(),
        )
        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True) as mock_conn_rec,
            mock.patch.object(
                test_module, "V20CredManager", autospec=True
            ) as mock_cred_mgr,
            mock.patch.object(
                test_module, "V20CredExRecord", autospec=True
            ) as mock_cx_rec_cls,
        ):
            mock_cx_rec.state = mock_cx_rec_cls.STATE_REQUEST_RECEIVED
            mock_cx_rec_cls.retrieve_by_id = mock.CoroutineMock(return_value=mock_cx_rec)

            # Emulate storage not found (bad connection id)
            mock_conn_rec.retrieve_by_id = mock.CoroutineMock(
                side_effect=test_module.StorageNotFoundError()
            )

            mock_cred_mgr.return_value.issue_credential = mock.CoroutineMock()
            mock_cred_mgr.return_value.issue_credential.return_value = (
                mock.MagicMock(),
                mock.MagicMock(),
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_issue(self.request)

    async def test_credential_exchange_issue_not_ready(self):
        self.request.json = mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True) as mock_conn_rec,
            mock.patch.object(
                test_module, "V20CredManager", autospec=True
            ) as mock_cred_mgr,
            mock.patch.object(
                test_module, "V20CredExRecord", autospec=True
            ) as mock_cx_rec,
        ):
            mock_cx_rec.retrieve_by_id = mock.CoroutineMock()
            mock_cx_rec.retrieve_by_id.return_value.state = (
                test_module.V20CredExRecord.STATE_REQUEST_RECEIVED
            )

            # Emulate connection not ready
            mock_conn_rec.retrieve_by_id = mock.CoroutineMock()
            mock_conn_rec.retrieve_by_id.return_value.is_ready = False

            mock_cred_mgr.return_value.issue_credential = mock.CoroutineMock()
            mock_cred_mgr.return_value.issue_credential.return_value = (
                mock.MagicMock(),
                mock.MagicMock(),
            )

            with self.assertRaises(test_module.web.HTTPForbidden):
                await test_module.credential_exchange_issue(self.request)

    async def test_credential_exchange_issue_rev_reg_full_indy(self):
        self.request.json = mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        mock_cx_rec = mock.MagicMock(
            conn_id="dummy",
            serialize=mock.MagicMock(),
            save_error_state=mock.CoroutineMock(),
        )
        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True) as mock_conn_rec,
            mock.patch.object(
                test_module, "V20CredManager", autospec=True
            ) as mock_cred_mgr,
            mock.patch.object(
                test_module, "V20CredExRecord", autospec=True
            ) as mock_cx_rec_cls,
        ):
            mock_cx_rec.state = mock_cx_rec_cls.STATE_REQUEST_RECEIVED
            mock_cx_rec_cls.retrieve_by_id = mock.CoroutineMock(return_value=mock_cx_rec)

            mock_conn_rec.retrieve_by_id = mock.CoroutineMock()
            mock_conn_rec.retrieve_by_id.return_value.is_ready = True

            mock_issue_cred = mock.CoroutineMock(
                side_effect=test_module.IndyIssuerError()
            )
            mock_cred_mgr.return_value.issue_credential = mock_issue_cred

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_issue(self.request)

    async def test_credential_exchange_issue_rev_reg_full_anoncreds(self):
        self.request.json = mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        mock_cx_rec = mock.MagicMock(
            conn_id="dummy",
            serialize=mock.MagicMock(),
            save_error_state=mock.CoroutineMock(),
        )
        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True) as mock_conn_rec,
            mock.patch.object(
                test_module, "V20CredManager", autospec=True
            ) as mock_cred_mgr,
            mock.patch.object(
                test_module, "V20CredExRecord", autospec=True
            ) as mock_cx_rec_cls,
        ):
            mock_cx_rec.state = mock_cx_rec_cls.STATE_REQUEST_RECEIVED
            mock_cx_rec_cls.retrieve_by_id = mock.CoroutineMock(return_value=mock_cx_rec)

            mock_conn_rec.retrieve_by_id = mock.CoroutineMock()
            mock_conn_rec.retrieve_by_id.return_value.is_ready = True

            mock_issue_cred = mock.AsyncMock(
                side_effect=test_module.AnonCredsIssuerError()
            )
            mock_cred_mgr.return_value.issue_credential = mock_issue_cred

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_issue(self.request)

    async def test_credential_exchange_issue_deser_x(self):
        self.request.json = mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        mock_cx_rec = V20CredExRecord(connection_id="dummy", cred_ex_id="dummy")
        mock_cx_rec.serialize = mock.MagicMock(side_effect=test_module.BaseModelError())
        mock_cx_rec.save_error_state = mock.CoroutineMock()

        mock_conn_rec = mock.MagicMock(ConnRecord, autospec=True)
        mock_conn_rec.retrieve_by_id = mock.CoroutineMock(return_value=ConnRecord())

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True) as mock_conn_rec,
            mock.patch.object(
                test_module, "V20CredManager", autospec=True
            ) as mock_cred_mgr,
            mock.patch.object(
                test_module, "V20CredExRecord", autospec=True
            ) as mock_cx_rec_cls,
        ):
            mock_cx_rec_cls.retrieve_by_id = mock.CoroutineMock(return_value=mock_cx_rec)
            mock_cred_mgr.return_value = mock.MagicMock(
                issue_credential=mock.CoroutineMock(
                    return_value=(
                        mock_cx_rec,
                        mock.MagicMock(),
                    )
                )
            )
            mock_cred_mgr.return_value.get_detail_record = mock.CoroutineMock(
                side_effect=[
                    mock.MagicMock(  # indy
                        serialize=mock.MagicMock(return_value={"...": "..."})
                    ),
                    None,  # ld_proof
                ]
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_issue(self.request)

    async def test_credential_exchange_store(self):
        self.request.json = mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True),
            mock.patch.object(
                test_module, "V20CredManager", autospec=True
            ) as mock_cred_mgr,
            mock.patch.object(
                test_module, "V20CredExRecord", autospec=True
            ) as mock_cx_rec_cls,
            mock.patch.object(test_module.web, "json_response") as mock_response,
            mock.patch.object(V20CredFormat.Format, "handler") as mock_handler,
        ):
            mock_cx_rec_cls.retrieve_by_id = mock.CoroutineMock()
            mock_cx_rec_cls.retrieve_by_id.return_value.state = (
                test_module.V20CredExRecord.STATE_CREDENTIAL_RECEIVED
            )
            mock_handler.return_value.get_detail_record = mock.CoroutineMock(
                side_effect=[
                    None,  # anoncreds
                    mock.MagicMock(  # indy
                        serialize=mock.MagicMock(return_value={"...": "..."})
                    ),
                    None,  # ld_proof
                    None,  # vc_di
                ]
            )

            mock_cx_rec = mock.MagicMock()

            mock_cred_mgr.return_value.store_credential.return_value = mock_cx_rec
            mock_cred_mgr.return_value.send_cred_ack.return_value = (
                mock_cx_rec,
                mock.MagicMock(),
            )

            await test_module.credential_exchange_store(self.request)

            mock_response.assert_called_once_with(
                {
                    "cred_ex_record": mock_cx_rec.serialize.return_value,
                    "anoncreds": None,
                    "indy": {"...": "..."},
                    "ld_proof": None,
                    "vc_di": None,
                }
            )

    async def test_credential_exchange_store_bad_cred_id_json(self):
        self.request.json = mock.CoroutineMock(
            side_effect=test_module.JSONDecodeError("Nope", "Nope", 0)
        )
        self.request.match_info = {"cred_ex_id": "dummy"}

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True) as mock_conn_rec,
            mock.patch.object(
                test_module, "V20CredManager", autospec=True
            ) as mock_cred_mgr,
            mock.patch.object(
                test_module, "V20CredExRecord", autospec=True
            ) as mock_cx_rec_cls,
            mock.patch.object(test_module.web, "json_response") as mock_response,
            mock.patch.object(
                LDProofCredFormatHandler, "get_detail_record", autospec=True
            ) as mock_ld_proof_get_detail_record,
            mock.patch.object(
                IndyCredFormatHandler, "get_detail_record", autospec=True
            ) as mock_indy_get_detail_record,
        ):
            mock_cx_rec_cls.retrieve_by_id = mock.CoroutineMock()
            mock_cx_rec_cls.retrieve_by_id.return_value.state = (
                test_module.V20CredExRecord.STATE_CREDENTIAL_RECEIVED
            )

            mock_cx_rec = V20CredExRecord(connection_id="dummy", cred_ex_id="dummy")
            mock_cx_rec.serialize = mock.MagicMock(
                return_value={"cred_ex_id": "dummy", "state": "credential_received"}
            )
            mock_cx_rec.save_error_state = mock.CoroutineMock()
            mock_cx_rec.connection_id = "dummy"

            mock_conn_rec = mock.MagicMock(ConnRecord, autospec=True)
            mock_conn_rec.retrieve_by_id = mock.CoroutineMock(return_value=ConnRecord())

            mock_indy_get_detail_record.return_value = mock.MagicMock(  # indy
                serialize=mock.MagicMock(return_value={"...": "..."})
            )
            mock_ld_proof_get_detail_record.return_value = None  # ld_proof

            mock_cred_mgr.return_value.store_credential.return_value = mock_cx_rec
            mock_cred_mgr.return_value.send_cred_ack.return_value = (
                mock_cx_rec,
                mock.MagicMock(),
            )

            await test_module.credential_exchange_store(self.request)

            mock_response.assert_called_once_with(
                {
                    "cred_ex_record": mock_cx_rec.serialize.return_value,
                    "anoncreds": None,
                    "indy": {"...": "..."},
                    "ld_proof": None,
                    "vc_di": None,
                }
            )

    async def test_credential_exchange_store_bad_cred_ex_id(self):
        self.request.json = mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with mock.patch.object(
            test_module, "V20CredExRecord", autospec=True
        ) as mock_cx_rec:
            mock_cx_rec.connection_id = "conn-123"
            mock_cx_rec.thread_id = "conn-123"
            mock_cx_rec.retrieve_by_id = mock.CoroutineMock()
            mock_cx_rec.retrieve_by_id.side_effect = test_module.StorageNotFoundError()

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.credential_exchange_store(self.request)

    async def test_credential_exchange_store_no_conn_record(self):
        self.request.json = mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True) as mock_conn_rec,
            mock.patch.object(
                test_module, "V20CredManager", autospec=True
            ) as mock_cred_mgr,
            mock.patch.object(
                test_module, "V20CredExRecord", autospec=True
            ) as mock_cx_rec,
        ):
            mock_cx_rec.connection_id = "conn-123"
            mock_cx_rec.thread_id = "conn-123"
            mock_cx_rec.retrieve_by_id = mock.CoroutineMock(
                return_value=mock.MagicMock(
                    state=mock_cx_rec.STATE_CREDENTIAL_RECEIVED,
                    save_error_state=mock.CoroutineMock(),
                )
            )

            # Emulate storage not found (bad connection id)
            mock_conn_rec.retrieve_by_id = mock.CoroutineMock(
                side_effect=test_module.StorageNotFoundError()
            )

            mock_cred_mgr.return_value.store_credential.return_value = mock_cx_rec
            mock_cred_mgr.return_value.send_cred_ack.return_value = (
                mock_cx_rec,
                mock.MagicMock(),
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_store(self.request)

    async def test_credential_exchange_store_not_ready(self):
        self.request.json = mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True) as mock_conn_rec,
            mock.patch.object(test_module, "V20CredManager", autospec=True),
            mock.patch.object(
                test_module, "V20CredExRecord", autospec=True
            ) as mock_cx_rec,
        ):
            mock_cx_rec.connection_id = "conn-123"
            mock_cx_rec.thread_id = "conn-123"
            mock_cx_rec.retrieve_by_id = mock.CoroutineMock()
            mock_cx_rec.retrieve_by_id.return_value.state = (
                test_module.V20CredExRecord.STATE_CREDENTIAL_RECEIVED
            )

            # Emulate connection not ready
            mock_conn_rec.retrieve_by_id = mock.CoroutineMock()
            mock_conn_rec.retrieve_by_id.return_value.is_ready = False

            with self.assertRaises(test_module.web.HTTPForbidden):
                await test_module.credential_exchange_store(self.request)

    async def test_credential_exchange_store_x(self):
        self.request.json = mock.CoroutineMock()
        self.request.match_info = {"cred_ex_id": "dummy"}

        with (
            mock.patch.object(test_module, "ConnRecord", autospec=True),
            mock.patch.object(
                test_module, "V20CredManager", autospec=True
            ) as mock_cred_mgr,
            mock.patch.object(
                test_module, "V20CredExRecord", autospec=True
            ) as mock_cx_rec_cls,
            mock.patch.object(test_module.web, "json_response"),
            mock.patch.object(V20CredFormat.Format, "handler") as mock_handler,
        ):
            mock_cx_rec = mock.MagicMock(
                state=mock_cx_rec_cls.STATE_CREDENTIAL_RECEIVED,
                serialize=mock.MagicMock(side_effect=test_module.BaseModelError()),
                save_error_state=mock.CoroutineMock(),
            )
            mock_cx_rec_cls.retrieve_by_id = mock.CoroutineMock(
                return_value=mock.MagicMock()
            )
            mock_handler.return_value.get_detail_record = mock.CoroutineMock(
                side_effect=[
                    None,  # anoncreds
                    mock.MagicMock(  # indy
                        serialize=mock.MagicMock(return_value={"...": "..."})
                    ),
                    None,  # ld_proof
                    None,  # vc_di
                ]
            )

            mock_cred_mgr.return_value = mock.MagicMock(
                store_credential=mock.CoroutineMock(return_value=mock_cx_rec),
                send_cred_ack=mock.CoroutineMock(
                    return_value=(
                        mock_cx_rec,
                        mock.MagicMock(),
                    )
                ),
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_store(self.request)

    async def test_credential_exchange_remove(self):
        self.request.match_info = {"cred_ex_id": "dummy"}

        with (
            mock.patch.object(
                test_module, "V20CredManager", autospec=True
            ) as mock_cred_mgr,
            mock.patch.object(test_module.web, "json_response") as mock_response,
        ):
            mock_cred_mgr.return_value = mock.MagicMock(
                delete_cred_ex_record=mock.CoroutineMock()
            )
            await test_module.credential_exchange_remove(self.request)

            mock_response.assert_called_once_with({})

    async def test_credential_exchange_remove_bad_cred_ex_id(self):
        self.request.match_info = {"cred_ex_id": "dummy"}

        with mock.patch.object(
            test_module, "V20CredManager", autospec=True
        ) as mock_cred_mgr:
            mock_cred_mgr.return_value = mock.MagicMock(
                delete_cred_ex_record=mock.CoroutineMock(
                    side_effect=test_module.StorageNotFoundError()
                )
            )

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.credential_exchange_remove(self.request)

    async def test_credential_exchange_remove_x(self):
        self.request.match_info = {"cred_ex_id": "dummy"}

        with mock.patch.object(
            test_module, "V20CredManager", autospec=True
        ) as mock_cred_mgr:
            mock_cred_mgr.return_value = mock.MagicMock(
                delete_cred_ex_record=mock.CoroutineMock(
                    side_effect=test_module.StorageError()
                )
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_remove(self.request)

    async def test_credential_exchange_problem_report(self):
        self.request.json = mock.CoroutineMock(
            return_value={"description": "Did I say no problem? I meant 'no: problem.'"}
        )
        self.request.match_info = {"cred_ex_id": "dummy"}
        magic_report = mock.MagicMock()

        with (
            mock.patch.object(test_module, "V20CredManager", autospec=True),
            mock.patch.object(
                test_module, "V20CredExRecord", autospec=True
            ) as mock_cred_ex,
            mock.patch.object(
                test_module, "problem_report_for_record", mock.MagicMock()
            ) as mock_problem_report,
            mock.patch.object(test_module.web, "json_response") as mock_response,
        ):
            mock_cred_ex.retrieve_by_id = mock.CoroutineMock(
                return_value=mock.MagicMock(save_error_state=mock.CoroutineMock())
            )
            mock_problem_report.return_value = magic_report

            await test_module.credential_exchange_problem_report(self.request)

            self.request["outbound_message_router"].assert_awaited_once_with(
                magic_report,
                connection_id=mock_cred_ex.retrieve_by_id.return_value.connection_id,
            )
            mock_response.assert_called_once_with({})

    async def test_credential_exchange_problem_report_bad_cred_ex_id(self):
        self.request.json = mock.CoroutineMock(
            return_value={"description": "Did I say no problem? I meant 'no: problem.'"}
        )
        self.request.match_info = {"cred_ex_id": "dummy"}

        with (
            mock.patch.object(test_module, "V20CredManager", autospec=True),
            mock.patch.object(
                test_module, "V20CredExRecord", autospec=True
            ) as mock_cred_ex,
        ):
            mock_cred_ex.retrieve_by_id = mock.CoroutineMock(
                side_effect=test_module.StorageNotFoundError()
            )

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.credential_exchange_problem_report(self.request)

    async def test_credential_exchange_problem_report_x(self):
        self.request.json = mock.CoroutineMock(
            return_value={"description": "Did I say no problem? I meant 'no: problem.'"}
        )
        self.request.match_info = {"cred_ex_id": "dummy"}

        with (
            mock.patch.object(test_module, "V20CredManager", autospec=True),
            mock.patch.object(test_module, "problem_report_for_record", mock.MagicMock()),
            mock.patch.object(
                test_module, "V20CredExRecord", autospec=True
            ) as mock_cred_ex,
        ):
            mock_cred_ex.retrieve_by_id = mock.CoroutineMock(
                return_value=mock.MagicMock(
                    save_error_state=mock.CoroutineMock(
                        side_effect=test_module.StorageError()
                    )
                )
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_exchange_problem_report(self.request)

    async def test_register(self):
        mock_app = mock.MagicMock()
        mock_app.add_routes = mock.MagicMock()

        await test_module.register(mock_app)
        mock_app.add_routes.assert_called_once()

    async def test_post_process_routes(self):
        mock_app = mock.MagicMock(_state={"swagger_dict": {}})
        test_module.post_process_routes(mock_app)
        assert "tags" in mock_app._state["swagger_dict"]
