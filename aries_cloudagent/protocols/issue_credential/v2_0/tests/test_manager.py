import asyncio
import json

from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock
from copy import deepcopy
from time import time

from .....core.in_memory import InMemoryProfile
from .....cache.base import BaseCache
from .....cache.in_memory import InMemoryCache
from .....indy.issuer import IndyIssuer
from .....messaging.decorators.attach_decorator import AttachDecorator
from .....messaging.responder import BaseResponder, MockResponder
from .....ledger.base import BaseLedger
from .....storage.error import StorageNotFoundError

from .. import manager as test_module
from ..manager import V20CredManager, V20CredManagerError
from ..message_types import (
    ATTACHMENT_FORMAT,
    CRED_20_PROPOSAL,
    CRED_20_OFFER,
    CRED_20_REQUEST,
    CRED_20_ISSUE,
)
from ..messages.cred_ack import V20CredAck
from ..messages.cred_issue import V20CredIssue
from ..messages.cred_format import V20CredFormat
from ..messages.cred_offer import V20CredOffer
from ..messages.cred_problem_report import V20CredProblemReport
from ..messages.cred_proposal import V20CredProposal
from ..messages.cred_request import V20CredRequest
from ..messages.inner.cred_preview import V20CredPreview, V20CredAttrSpec
from ..models.cred_ex_record import V20CredExRecord


TEST_DID = "LjgpST2rjsoxYegQDRm7EL"
SCHEMA_NAME = "bc-reg"
SCHEMA_TXN = 12
SCHEMA_ID = f"{TEST_DID}:2:{SCHEMA_NAME}:1.0"
SCHEMA = {
    "ver": "1.0",
    "id": SCHEMA_ID,
    "name": SCHEMA_NAME,
    "version": "1.0",
    "attrNames": ["legalName", "jurisdictionId", "incorporationDate"],
    "seqNo": SCHEMA_TXN,
}
CRED_DEF_ID = f"{TEST_DID}:3:CL:12:tag1"
CRED_DEF = {
    "ver": "1.0",
    "id": CRED_DEF_ID,
    "schemaId": SCHEMA_TXN,
    "type": "CL",
    "tag": "tag1",
    "value": {
        "primary": {
            "n": "...",
            "s": "...",
            "r": {
                "master_secret": "...",
                "legalName": "...",
                "busId": "...",
                "jurisdictionId": "...",
                "incorporationDate": "...",
                "pic": "...",
            },
            "rctxt": "...",
            "z": "...",
        },
        "revocation": {
            "g": "1 ...",
            "g_dash": "1 ...",
            "h": "1 ...",
            "h0": "1 ...",
            "h1": "1 ...",
            "h2": "1 ...",
            "htilde": "1 ...",
            "h_cap": "1 ...",
            "u": "1 ...",
            "pk": "1 ...",
            "y": "1 ...",
        },
    },
}
REV_REG_DEF_TYPE = "CL_ACCUM"
REV_REG_ID = f"{TEST_DID}:4:{CRED_DEF_ID}:{REV_REG_DEF_TYPE}:tag1"
TAILS_DIR = "/tmp/indy/revocation/tails_files"
TAILS_HASH = "8UW1Sz5cqoUnK9hqQk7nvtKK65t7Chu3ui866J23sFyJ"
TAILS_LOCAL = f"{TAILS_DIR}/{TAILS_HASH}"
REV_REG_DEF = {
    "ver": "1.0",
    "id": REV_REG_ID,
    "revocDefType": "CL_ACCUM",
    "tag": "tag1",
    "credDefId": CRED_DEF_ID,
    "value": {
        "issuanceType": "ISSUANCE_ON_DEMAND",
        "maxCredNum": 5,
        "publicKeys": {"accumKey": {"z": "1 ..."}},
        "tailsHash": TAILS_HASH,
        "tailsLocation": TAILS_LOCAL,
    },
}
INDY_OFFER = {
    "schema_id": SCHEMA_ID,
    "cred_def_id": CRED_DEF_ID,
    "key_correctness_proof": {
        "c": "123467890",
        "xz_cap": "12345678901234567890",
        "xr_cap": [
            [
                "remainder",
                "1234567890",
            ],
            [
                "number",
                "12345678901234",
            ],
            [
                "master_secret",
                "12345678901234",
            ],
        ],
    },
    "nonce": "1234567890",
}
INDY_CRED_REQ = {
    "prover_did": TEST_DID,
    "cred_def_id": CRED_DEF_ID,
    "blinded_ms": {
        "u": "12345",
        "ur": "1 123467890ABCDEF",
        "hidden_attributes": ["master_secret"],
        "committed_attributes": {},
    },
    "blinded_ms_correctness_proof": {
        "c": "77777",
        "v_dash_cap": "12345678901234567890",
        "m_caps": {"master_secret": "271283714"},
        "r_caps": {},
    },
    "nonce": "9876543210",
}
INDY_CRED = {
    "schema_id": SCHEMA_ID,
    "cred_def_id": CRED_DEF_ID,
    "rev_reg_id": REV_REG_ID,
    "values": {
        "legalName": {
            "raw": "The Original House of Pies",
            "encoded": "108156129846915621348916581250742315326283968964",
        },
        "busId": {"raw": "11155555", "encoded": "11155555"},
        "jurisdictionId": {"raw": "1", "encoded": "1"},
        "incorporationDate": {
            "raw": "2021-01-01",
            "encoded": "121381685682968329568231",
        },
        "pic": {"raw": "cG90YXRv", "encoded": "125362825623562385689562"},
    },
    "signature": {
        "p_credential": {
            "m_2": "13683295623862356",
            "a": "1925723185621385238953",
            "e": "253516862326",
            "v": "26890295622385628356813632",
        },
        "r_credential": {
            "sigma": "1 00F81D",
            "c": "158698926BD09866E",
            "vr_prime_prime": "105682396DDF1A",
            "witness_signature": {"sigma_i": "1 ...", "u_i": "1 ...", "g_i": "1 ..."},
            "g_i": "1 ...",
            "i": 1,
            "m2": "862186285926592362384FA97FF3A4AB",
        },
    },
    "signature_correctness_proof": {
        "se": "10582965928638296868123",
        "c": "2816389562839651",
    },
    "rev_reg": {"accum": "21 ..."},
    "witness": {"omega": "21 ..."},
}

LD_PROOF_VC_DETAIL = {
    "credential": {
        "@context": ["https://www.w3.org/2018/credentials/v1"],
        "type": ["VerifiableCredential"],
        "credentialSubject": {"test": "key"},
        "issuanceDate": "2021-04-12",
        "issuer": f"did:sov:{TEST_DID}",
    },
    "options": {"proofType": "Ed25519Signature2018"},
}
LD_PROOF_VC = {
    "@context": ["https://www.w3.org/2018/credentials/v1"],
    "type": ["VerifiableCredential"],
    "credentialSubject": {"test": "key"},
    "issuanceDate": "2021-04-12",
    "issuer": f"did:sov:{TEST_DID}",
    "proof": {
        "proofPurpose": "assertionMethod",
        "created": "2019-12-11T03:50:55",
        "type": "Ed25519Signature2018",
        "verificationMethod": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
        "jws": "eyJhbGciOiAiRWREU0EiLCAiYjY0IjogZmFsc2UsICJjcml0IjogWyJiNjQiXX0..Q6amIrxGiSbM7Ce6DxlfwLCjVcYyclas8fMxaecspXFUcFW9DAAxKzgHx93FWktnlZjM_biitkMgZdStgvivAQ",
    },
}


class TestV20CredManager(AsyncTestCase):
    async def setUp(self):
        self.session = InMemoryProfile.test_session()
        self.profile = self.session.profile
        self.context = self.profile.context
        setattr(
            self.profile, "session", async_mock.MagicMock(return_value=self.session)
        )

        Ledger = async_mock.MagicMock()
        self.ledger = Ledger()
        self.ledger.get_schema = async_mock.CoroutineMock(return_value=SCHEMA)
        self.ledger.get_credential_definition = async_mock.CoroutineMock(
            return_value=CRED_DEF
        )
        self.ledger.get_revoc_reg_def = async_mock.CoroutineMock(
            return_value=REV_REG_DEF
        )
        self.ledger.__aenter__ = async_mock.CoroutineMock(return_value=self.ledger)
        self.ledger.credential_definition_id2schema_id = async_mock.CoroutineMock(
            return_value=SCHEMA_ID
        )
        self.context.injector.bind_instance(BaseLedger, self.ledger)

        self.manager = V20CredManager(self.profile)
        assert self.manager.profile

    async def test_prepare_send(self):
        connection_id = "test_conn_id"
        cred_preview = V20CredPreview(
            attributes=(
                V20CredAttrSpec(name="legalName", value="value"),
                V20CredAttrSpec(name="jurisdictionId", value="value"),
                V20CredAttrSpec(name="incorporationDate", value="value"),
            )
        )
        cred_proposal = V20CredProposal(
            credential_preview=cred_preview,
            formats=[
                V20CredFormat(
                    attach_id="0",
                    format_=ATTACHMENT_FORMAT[CRED_20_PROPOSAL][
                        V20CredFormat.Format.INDY.api
                    ],
                )
            ],
            filters_attach=[
                AttachDecorator.data_base64(
                    {"cred_def_id": CRED_DEF_ID, "schema_id": SCHEMA_ID}, ident="0"
                )
            ],
        )
        with async_mock.patch.object(
            self.manager, "create_offer", autospec=True
        ) as create_offer:
            create_offer.return_value = (async_mock.MagicMock(), async_mock.MagicMock())
            ret_cred_ex_rec, ret_cred_offer = await self.manager.prepare_send(
                connection_id, cred_proposal
            )
            create_offer.assert_called_once()
            assert ret_cred_ex_rec is create_offer.return_value[0]
            arg_cred_ex_rec = create_offer.call_args[1]["cred_ex_record"]
            assert arg_cred_ex_rec.auto_issue
            assert arg_cred_ex_rec.connection_id == connection_id
            assert arg_cred_ex_rec.role == V20CredExRecord.ROLE_ISSUER
            assert arg_cred_ex_rec.cred_proposal == cred_proposal.serialize()

    async def test_create_proposal(self):
        connection_id = "test_conn_id"
        comment = "comment"
        cred_preview = V20CredPreview(
            attributes=(
                V20CredAttrSpec(name="legalName", value="value"),
                V20CredAttrSpec(name="jurisdictionId", value="value"),
                V20CredAttrSpec(name="incorporationDate", value="value"),
            )
        )

        with async_mock.patch.object(
            V20CredExRecord, "save", autospec=True
        ) as mock_save, async_mock.patch.object(
            V20CredFormat.Format, "handler"
        ) as mock_handler:

            mock_handler.return_value.create_proposal = async_mock.CoroutineMock(
                return_value=(
                    V20CredFormat(
                        attach_id=V20CredFormat.Format.INDY.api,
                        format_=ATTACHMENT_FORMAT[CRED_20_PROPOSAL][
                            V20CredFormat.Format.INDY.api
                        ],
                    ),
                    AttachDecorator.data_base64(
                        {}, ident=V20CredFormat.Format.INDY.api
                    ),
                )
            )
            cx_rec = await self.manager.create_proposal(
                connection_id,
                comment=comment,
                cred_preview=cred_preview,
                fmt2filter={V20CredFormat.Format.INDY: None},
            )  # leave underspecified until offer receipt
            mock_save.assert_called_once()
            mock_handler.return_value.create_proposal.assert_called_once_with(
                cx_rec, None
            )

        cred_proposal = V20CredProposal.deserialize(cx_rec.cred_proposal)
        assert not cred_proposal.attachment(
            V20CredFormat.Format.INDY
        ).keys()  # leave underspecified until offer receipt
        assert cx_rec.connection_id == connection_id
        assert cx_rec.thread_id == cred_proposal._thread_id
        assert cx_rec.role == V20CredExRecord.ROLE_HOLDER
        assert cx_rec.state == V20CredExRecord.STATE_PROPOSAL_SENT
        assert cx_rec.cred_preview == cred_preview.serialize()

    async def test_create_proposal_no_preview(self):
        connection_id = "test_conn_id"
        comment = "comment"

        with async_mock.patch.object(
            V20CredExRecord, "save", autospec=True
        ) as mock_save, async_mock.patch.object(
            V20CredFormat.Format, "handler"
        ) as mock_handler:

            mock_handler.return_value.create_proposal = async_mock.CoroutineMock(
                return_value=(
                    V20CredFormat(
                        attach_id=V20CredFormat.Format.LD_PROOF.api,
                        format_=ATTACHMENT_FORMAT[CRED_20_PROPOSAL][
                            V20CredFormat.Format.LD_PROOF.api
                        ],
                    ),
                    AttachDecorator.data_base64(
                        LD_PROOF_VC_DETAIL,
                        ident=V20CredFormat.Format.LD_PROOF.api,
                    ),
                )
            )
            cx_rec = await self.manager.create_proposal(
                connection_id,
                comment=comment,
                cred_preview=None,
                fmt2filter={V20CredFormat.Format.LD_PROOF: LD_PROOF_VC_DETAIL},
            )
            mock_save.assert_called_once()
            mock_handler.return_value.create_proposal.assert_called_once_with(
                cx_rec, LD_PROOF_VC_DETAIL
            )

        cred_proposal = V20CredProposal.deserialize(cx_rec.cred_proposal)
        assert (
            cred_proposal.attachment(V20CredFormat.Format.LD_PROOF)
            == LD_PROOF_VC_DETAIL
        )
        assert cx_rec.connection_id == connection_id
        assert cx_rec.thread_id == cred_proposal._thread_id
        assert cx_rec.role == V20CredExRecord.ROLE_HOLDER
        assert cx_rec.state == V20CredExRecord.STATE_PROPOSAL_SENT

    async def test_receive_proposal(self):
        connection_id = "test_conn_id"

        cred_preview = V20CredPreview(
            attributes=(
                V20CredAttrSpec(name="legalName", value="value"),
                V20CredAttrSpec(name="jurisdictionId", value="value"),
                V20CredAttrSpec(name="incorporationDate", value="value"),
            )
        )

        with async_mock.patch.object(
            V20CredExRecord, "save", autospec=True
        ) as mock_save, async_mock.patch.object(
            V20CredFormat.Format, "handler"
        ) as mock_handler:

            mock_handler.return_value.receive_proposal = async_mock.CoroutineMock()

            cred_proposal = V20CredProposal(
                credential_preview=cred_preview,
                formats=[
                    V20CredFormat(
                        attach_id="0",
                        format_=ATTACHMENT_FORMAT[CRED_20_PROPOSAL][
                            V20CredFormat.Format.INDY.api
                        ],
                    )
                ],
                filters_attach=[
                    AttachDecorator.data_base64({"cred_def_id": CRED_DEF_ID}, ident="0")
                ],
            )

            cx_rec = await self.manager.receive_proposal(cred_proposal, connection_id)
            mock_save.assert_called_once()
            mock_handler.return_value.receive_proposal.assert_called_once_with(
                cx_rec, cred_proposal
            )

            ret_cred_proposal = V20CredProposal.deserialize(cx_rec.cred_proposal)

            assert ret_cred_proposal.attachment(V20CredFormat.Format.INDY) == {
                "cred_def_id": CRED_DEF_ID
            }
            assert (
                ret_cred_proposal.credential_preview.attributes
                == cred_preview.attributes
            )
            assert cx_rec.connection_id == connection_id
            assert cx_rec.role == V20CredExRecord.ROLE_ISSUER
            assert cx_rec.state == V20CredExRecord.STATE_PROPOSAL_RECEIVED
            assert cx_rec.thread_id == cred_proposal._thread_id

    async def test_create_free_offer(self):
        comment = "comment"

        cred_preview = V20CredPreview(
            attributes=(
                V20CredAttrSpec(name="legalName", value="value"),
                V20CredAttrSpec(name="jurisdictionId", value="value"),
                V20CredAttrSpec(name="incorporationDate", value="value"),
            )
        )
        cred_proposal = V20CredProposal(
            credential_preview=cred_preview,
            formats=[
                V20CredFormat(
                    attach_id="0",
                    format_=ATTACHMENT_FORMAT[CRED_20_PROPOSAL][
                        V20CredFormat.Format.INDY.api
                    ],
                )
            ],
            filters_attach=[
                AttachDecorator.data_base64({"cred_def_id": CRED_DEF_ID}, ident="0")
            ],
        )

        cx_rec = V20CredExRecord(
            cred_ex_id="dummy-cxid",
            role=V20CredExRecord.ROLE_ISSUER,
            cred_proposal=cred_proposal.serialize(),
        )

        with async_mock.patch.object(
            V20CredExRecord, "save", autospec=True
        ) as mock_save, async_mock.patch.object(
            V20CredFormat.Format, "handler"
        ) as mock_handler:

            mock_handler.return_value.create_offer = async_mock.CoroutineMock(
                return_value=(
                    V20CredFormat(
                        attach_id=V20CredFormat.Format.INDY.api,
                        format_=ATTACHMENT_FORMAT[CRED_20_PROPOSAL][
                            V20CredFormat.Format.INDY.api
                        ],
                    ),
                    AttachDecorator.data_base64(
                        INDY_OFFER, ident=V20CredFormat.Format.INDY.api
                    ),
                )
            )

            (ret_cx_rec, ret_offer) = await self.manager.create_offer(
                cred_ex_record=cx_rec,
                counter_proposal=None,
                replacement_id="0",
                comment=comment,
            )
            assert ret_cx_rec == cx_rec
            mock_save.assert_called_once()

            mock_handler.return_value.create_offer.assert_called_once_with(cx_rec)

            assert cx_rec.cred_ex_id == ret_cx_rec._id  # cover property
            assert cx_rec.thread_id == ret_offer._thread_id
            assert cx_rec.role == V20CredExRecord.ROLE_ISSUER
            assert cx_rec.state == V20CredExRecord.STATE_OFFER_SENT
            assert (
                V20CredOffer.deserialize(cx_rec.cred_offer).attachment(
                    V20CredFormat.Format.INDY
                )
                == INDY_OFFER
            )

            await self.manager.create_offer(
                cred_ex_record=cx_rec,
                counter_proposal=None,
                replacement_id="0",
                comment=comment,
            )  # once more to cover case where offer is available in cache

    async def test_create_bound_offer(self):
        comment = "comment"

        cred_preview = V20CredPreview(
            attributes=(
                V20CredAttrSpec(name="legalName", value="value"),
                V20CredAttrSpec(name="jurisdictionId", value="value"),
                V20CredAttrSpec(name="incorporationDate", value="value"),
            )
        )
        cred_proposal = V20CredProposal(
            credential_preview=cred_preview,
            formats=[
                V20CredFormat(
                    attach_id="0",
                    format_=ATTACHMENT_FORMAT[CRED_20_PROPOSAL][
                        V20CredFormat.Format.INDY.api
                    ],
                )
            ],
            filters_attach=[
                AttachDecorator.data_base64({"cred_def_id": CRED_DEF_ID}, ident="0")
            ],
        )
        cx_rec = V20CredExRecord(
            cred_ex_id="dummy-cxid",
            role=V20CredExRecord.ROLE_ISSUER,
            cred_proposal=cred_proposal.serialize(),
        )

        with async_mock.patch.object(
            V20CredExRecord, "save", autospec=True
        ) as mock_save, async_mock.patch.object(
            V20CredFormat.Format, "handler"
        ) as mock_handler:
            mock_handler.return_value.create_offer = async_mock.CoroutineMock(
                return_value=(
                    V20CredFormat(
                        attach_id=V20CredFormat.Format.INDY.api,
                        format_=ATTACHMENT_FORMAT[CRED_20_OFFER][
                            V20CredFormat.Format.INDY.api
                        ],
                    ),
                    AttachDecorator.data_base64(
                        INDY_OFFER, ident=V20CredFormat.Format.INDY.api
                    ),
                )
            )

            (ret_cx_rec, ret_offer) = await self.manager.create_offer(
                cred_ex_record=cx_rec,
                counter_proposal=None,
                comment=comment,
            )
            assert ret_cx_rec == cx_rec
            mock_save.assert_called_once()

            mock_handler.return_value.create_offer.assert_called_once_with(cx_rec)

            assert cx_rec.thread_id == ret_offer._thread_id
            assert cx_rec.role == V20CredExRecord.ROLE_ISSUER
            assert cx_rec.state == V20CredExRecord.STATE_OFFER_SENT
            assert (
                V20CredOffer.deserialize(cx_rec.cred_offer).attachment(
                    V20CredFormat.Format.INDY
                )
                == INDY_OFFER
            )

            # additionally check that manager passed credential preview through
            assert ret_offer.credential_preview.attributes == cred_preview.attributes

    async def test_create_offer_x_no_formats(self):
        comment = "comment"

        cred_proposal = V20CredProposal(
            formats=[],
            filters_attach=[],
        )

        cx_rec = V20CredExRecord(
            cred_ex_id="dummy-cxid",
            role=V20CredExRecord.ROLE_ISSUER,
            cred_proposal=cred_proposal.serialize(),
        )

        with self.assertRaises(V20CredManagerError) as context:
            await self.manager.create_offer(
                cred_ex_record=cx_rec,
                counter_proposal=None,
                comment=comment,
            )
        assert "No supported formats" in str(context.exception)

    async def test_receive_offer_proposed(self):
        connection_id = "test_conn_id"
        thread_id = "thread-id"

        cred_preview = V20CredPreview(
            attributes=(
                V20CredAttrSpec(name="legalName", value="value"),
                V20CredAttrSpec(name="jurisdictionId", value="value"),
                V20CredAttrSpec(name="incorporationDate", value="value"),
            )
        )
        cred_proposal = V20CredProposal(
            credential_preview=cred_preview,
            formats=[
                V20CredFormat(
                    attach_id="0",
                    format_=ATTACHMENT_FORMAT[CRED_20_PROPOSAL][
                        V20CredFormat.Format.INDY.api
                    ],
                )
            ],
            filters_attach=[AttachDecorator.data_base64({}, ident="0")],
        )
        cred_offer = V20CredOffer(
            credential_preview=cred_preview,
            formats=[
                V20CredFormat(
                    attach_id="0",
                    format_=ATTACHMENT_FORMAT[CRED_20_OFFER][
                        V20CredFormat.Format.INDY.api
                    ],
                )
            ],
            offers_attach=[AttachDecorator.data_base64(INDY_OFFER, ident="0")],
        )
        cred_offer.assign_thread_id(thread_id)

        stored_cx_rec = V20CredExRecord(
            cred_ex_id="dummy-cxid",
            connection_id=connection_id,
            cred_proposal=cred_proposal.serialize(),
            initiator=V20CredExRecord.INITIATOR_EXTERNAL,
            role=V20CredExRecord.ROLE_HOLDER,
            thread_id=thread_id,
        )

        with async_mock.patch.object(
            V20CredExRecord, "save", autospec=True
        ) as mock_save, async_mock.patch.object(
            V20CredExRecord,
            "retrieve_by_conn_and_thread",
            async_mock.CoroutineMock(return_value=stored_cx_rec),
        ) as mock_retrieve, async_mock.patch.object(
            V20CredFormat.Format, "handler"
        ) as mock_handler:
            mock_handler.return_value.receive_offer = async_mock.CoroutineMock()

            cx_rec = await self.manager.receive_offer(cred_offer, connection_id)

            mock_handler.return_value.receive_offer.assert_called_once_with(
                cx_rec, cred_offer
            )

            assert cx_rec.connection_id == connection_id
            assert cx_rec.thread_id == cred_offer._thread_id
            assert cx_rec.role == V20CredExRecord.ROLE_HOLDER
            assert cx_rec.state == V20CredExRecord.STATE_OFFER_RECEIVED
            assert (
                V20CredOffer.deserialize(cx_rec.cred_offer).attachment(
                    V20CredFormat.Format.INDY
                )
                == INDY_OFFER
            )
            assert (
                V20CredProposal.deserialize(
                    cx_rec.cred_proposal
                ).credential_preview.attributes
                == cred_preview.attributes
            )

    async def test_receive_free_offer(self):
        connection_id = "test_conn_id"
        thread_id = "thread-id"

        cred_preview = V20CredPreview(
            attributes=(
                V20CredAttrSpec(name="legalName", value="value"),
                V20CredAttrSpec(name="jurisdictionId", value="value"),
                V20CredAttrSpec(name="incorporationDate", value="value"),
            )
        )
        cred_offer = V20CredOffer(
            credential_preview=cred_preview,
            formats=[
                V20CredFormat(
                    attach_id="0",
                    format_=ATTACHMENT_FORMAT[CRED_20_OFFER][
                        V20CredFormat.Format.INDY.api
                    ],
                )
            ],
            offers_attach=[AttachDecorator.data_base64(INDY_OFFER, ident="0")],
        )
        cred_offer.assign_thread_id(thread_id)

        self.context.message = cred_offer
        self.context.conn_record = async_mock.MagicMock()
        self.context.conn_record.connection_id = connection_id

        with async_mock.patch.object(
            V20CredExRecord, "save", autospec=True
        ) as mock_save, async_mock.patch.object(
            V20CredExRecord, "retrieve_by_conn_and_thread", async_mock.CoroutineMock()
        ) as mock_retrieve, async_mock.patch.object(
            V20CredFormat.Format, "handler"
        ) as mock_handler:
            mock_handler.return_value.receive_offer = async_mock.CoroutineMock()
            mock_retrieve.side_effect = (StorageNotFoundError(),)
            cx_rec = await self.manager.receive_offer(cred_offer, connection_id)

            mock_handler.return_value.receive_offer.assert_called_once_with(
                cx_rec, cred_offer
            )

            assert cx_rec.connection_id == connection_id
            assert cx_rec.thread_id == cred_offer._thread_id
            assert cx_rec.role == V20CredExRecord.ROLE_HOLDER
            assert cx_rec.state == V20CredExRecord.STATE_OFFER_RECEIVED
            assert (
                V20CredOffer.deserialize(cx_rec.cred_offer).attachment(
                    V20CredFormat.Format.INDY
                )
                == INDY_OFFER
            )
            assert not cx_rec.cred_proposal

    async def test_create_bound_request(self):
        connection_id = "test_conn_id"
        thread_id = "thread-id"
        holder_did = "did"

        cred_offer = V20CredOffer(
            formats=[
                V20CredFormat(
                    attach_id="0",
                    format_=ATTACHMENT_FORMAT[CRED_20_OFFER][
                        V20CredFormat.Format.INDY.api
                    ],
                )
            ],
            offers_attach=[AttachDecorator.data_base64(INDY_OFFER, ident="0")],
        )
        cred_offer.assign_thread_id(thread_id)

        stored_cx_rec = V20CredExRecord(
            cred_ex_id="dummy-cxid",
            connection_id=connection_id,
            cred_offer=cred_offer.serialize(),
            initiator=V20CredExRecord.INITIATOR_SELF,
            role=V20CredExRecord.ROLE_HOLDER,
            state=V20CredExRecord.STATE_OFFER_RECEIVED,
            thread_id=thread_id,
        )

        self.cache = InMemoryCache()
        self.context.injector.bind_instance(BaseCache, self.cache)

        with async_mock.patch.object(
            V20CredExRecord, "save", autospec=True
        ) as mock_save, async_mock.patch.object(
            V20CredFormat.Format, "handler"
        ) as mock_handler:

            mock_handler.return_value.create_request = async_mock.CoroutineMock(
                return_value=(
                    V20CredFormat(
                        attach_id=V20CredFormat.Format.INDY.api,
                        format_=ATTACHMENT_FORMAT[CRED_20_REQUEST][
                            V20CredFormat.Format.INDY.api
                        ],
                    ),
                    AttachDecorator.data_base64(
                        INDY_CRED_REQ, ident=V20CredFormat.Format.INDY.api
                    ),
                )
            )

            ret_cx_rec, ret_cred_req = await self.manager.create_request(
                stored_cx_rec, holder_did
            )

            mock_handler.return_value.create_request.assert_called_once_with(
                stored_cx_rec, {"holder_did": holder_did}
            )

            assert ret_cred_req.attachment() == INDY_CRED_REQ
            assert ret_cred_req._thread_id == thread_id

            assert ret_cx_rec.state == V20CredExRecord.STATE_REQUEST_SENT

    async def test_create_request_x_no_formats(self):
        comment = "comment"

        cred_proposal = V20CredProposal(
            formats=[],
            filters_attach=[],
        )

        cx_rec = V20CredExRecord(
            cred_ex_id="dummy-cxid",
            role=V20CredExRecord.ROLE_ISSUER,
            cred_proposal=cred_proposal.serialize(),
        )

        with self.assertRaises(V20CredManagerError) as context:
            await self.manager.create_request(
                cred_ex_record=cx_rec,
                holder_did="holder_did",
                comment=comment,
            )
        assert "No supported formats" in str(context.exception)

    async def test_create_free_request(self):
        connection_id = "test_conn_id"
        thread_id = "thread-id"
        holder_did = "did"

        cred_proposal = V20CredProposal(
            formats=[
                V20CredFormat(
                    attach_id="0",
                    format_=ATTACHMENT_FORMAT[CRED_20_PROPOSAL][
                        V20CredFormat.Format.LD_PROOF.api
                    ],
                )
            ],
            filters_attach=[AttachDecorator.data_base64(LD_PROOF_VC_DETAIL, ident="0")],
        )

        stored_cx_rec = V20CredExRecord(
            cred_ex_id="dummy-cxid",
            connection_id=connection_id,
            initiator=V20CredExRecord.INITIATOR_SELF,
            role=V20CredExRecord.ROLE_HOLDER,
            thread_id=thread_id,
            cred_proposal=cred_proposal.serialize(),
        )

        self.cache = InMemoryCache()
        self.context.injector.bind_instance(BaseCache, self.cache)

        with async_mock.patch.object(
            V20CredExRecord, "save", autospec=True
        ) as mock_save, async_mock.patch.object(
            V20CredFormat.Format, "handler"
        ) as mock_handler:

            mock_handler.return_value.create_request = async_mock.CoroutineMock(
                return_value=(
                    V20CredFormat(
                        attach_id=V20CredFormat.Format.LD_PROOF.api,
                        format_=ATTACHMENT_FORMAT[CRED_20_REQUEST][
                            V20CredFormat.Format.LD_PROOF.api
                        ],
                    ),
                    AttachDecorator.data_base64(
                        LD_PROOF_VC_DETAIL, ident=V20CredFormat.Format.LD_PROOF.api
                    ),
                )
            )

            ret_cx_rec, ret_cred_req = await self.manager.create_request(
                stored_cx_rec, holder_did
            )

            mock_handler.return_value.create_request.assert_called_once_with(
                stored_cx_rec, {"holder_did": holder_did}
            )

            assert ret_cred_req.attachment() == LD_PROOF_VC_DETAIL
            assert ret_cred_req._thread_id == thread_id

            assert ret_cx_rec.state == V20CredExRecord.STATE_REQUEST_SENT

    async def test_create_request_existing_cred_req(self):
        stored_cx_rec = V20CredExRecord(cred_request=async_mock.MagicMock())

        with self.assertRaises(V20CredManagerError) as context:
            await self.manager.create_request(stored_cx_rec, "did")
        assert "called multiple times" in str(context.exception)

    async def test_create_request_bad_state(self):
        holder_did = "did"

        stored_cx_rec = V20CredExRecord(
            state=V20CredExRecord.STATE_PROPOSAL_SENT,
        )

        with self.assertRaises(V20CredManagerError) as context:
            await self.manager.create_request(stored_cx_rec, holder_did)
        assert " state " in str(context.exception)

    async def test_receive_request(self):
        connection_id = "test_conn_id"
        stored_cx_rec = V20CredExRecord(
            cred_ex_id="dummy-cxid",
            connection_id=connection_id,
            initiator=V20CredExRecord.INITIATOR_EXTERNAL,
            role=V20CredExRecord.ROLE_ISSUER,
            state=V20CredExRecord.STATE_OFFER_SENT,
        )
        cred_request = V20CredRequest(
            formats=[
                V20CredFormat(
                    attach_id="0",
                    format_=ATTACHMENT_FORMAT[CRED_20_REQUEST][
                        V20CredFormat.Format.INDY.api
                    ],
                )
            ],
            requests_attach=[AttachDecorator.data_base64(INDY_CRED_REQ, ident="0")],
        )

        with async_mock.patch.object(
            V20CredExRecord, "save", autospec=True
        ) as mock_save, async_mock.patch.object(
            V20CredExRecord, "retrieve_by_conn_and_thread", async_mock.CoroutineMock()
        ) as mock_retrieve, async_mock.patch.object(
            V20CredFormat.Format, "handler"
        ) as mock_handler:
            mock_retrieve.side_effect = (StorageNotFoundError(),)
            mock_handler.return_value.receive_request = async_mock.CoroutineMock()
            # mock_retrieve.return_value = stored_cx_rec

            cx_rec = await self.manager.receive_request(cred_request, connection_id)

            mock_retrieve.assert_called_once_with(
                self.session, connection_id, cred_request._thread_id
            )
            mock_handler.return_value.receive_request.assert_called_once_with(
                cx_rec, cred_request
            )
            mock_save.assert_called_once()

            assert cx_rec.state == V20CredExRecord.STATE_REQUEST_RECEIVED
            assert (
                V20CredRequest.deserialize(cx_rec.cred_request).attachment()
                == INDY_CRED_REQ
            )

    async def test_issue_credential(self):
        connection_id = "test_conn_id"
        thread_id = "thread-id"
        comment = "comment"
        attr_values = {
            "legalName": "value",
            "jurisdictionId": "value",
            "incorporationDate": "value",
        }
        cred_preview = V20CredPreview(
            attributes=[
                V20CredAttrSpec(name=k, value=v) for (k, v) in attr_values.items()
            ]
        )
        cred_proposal = V20CredProposal(
            credential_preview=cred_preview,
            formats=[
                V20CredFormat(
                    attach_id="0",
                    format_=ATTACHMENT_FORMAT[CRED_20_PROPOSAL][
                        V20CredFormat.Format.INDY.api
                    ],
                )
            ],
            filters_attach=[
                AttachDecorator.data_base64(
                    {
                        "schema_id": SCHEMA_ID,
                        "cred_def_id": CRED_DEF_ID,
                    },
                    ident="0",
                )
            ],
        )
        cred_offer = V20CredOffer(
            formats=[
                V20CredFormat(
                    attach_id="0",
                    format_=ATTACHMENT_FORMAT[CRED_20_OFFER][
                        V20CredFormat.Format.INDY.api
                    ],
                )
            ],
            offers_attach=[AttachDecorator.data_base64(INDY_OFFER, ident="0")],
        )
        cred_offer.assign_thread_id(thread_id)
        cred_request = V20CredRequest(
            formats=[
                V20CredFormat(
                    attach_id="0",
                    format_=ATTACHMENT_FORMAT[CRED_20_REQUEST][
                        V20CredFormat.Format.INDY.api
                    ],
                )
            ],
            requests_attach=[AttachDecorator.data_base64(INDY_CRED_REQ, ident="0")],
        )

        stored_cx_rec = V20CredExRecord(
            cred_ex_id="dummy-cxid",
            connection_id=connection_id,
            cred_proposal=cred_proposal.serialize(),
            cred_offer=cred_offer.serialize(),
            cred_request=cred_request.serialize(),
            initiator=V20CredExRecord.INITIATOR_SELF,
            role=V20CredExRecord.ROLE_ISSUER,
            state=V20CredExRecord.STATE_REQUEST_RECEIVED,
            thread_id=thread_id,
        )

        issuer = async_mock.MagicMock()
        cred_rev_id = "1000"
        issuer.create_credential = async_mock.CoroutineMock(
            return_value=(json.dumps(INDY_CRED), cred_rev_id)
        )
        self.context.injector.bind_instance(IndyIssuer, issuer)

        with async_mock.patch.object(
            V20CredExRecord, "save", autospec=True
        ) as mock_save, async_mock.patch.object(
            V20CredFormat.Format, "handler"
        ) as mock_handler:

            mock_handler.return_value.issue_credential = async_mock.CoroutineMock(
                return_value=(
                    V20CredFormat(
                        attach_id=V20CredFormat.Format.INDY.api,
                        format_=ATTACHMENT_FORMAT[CRED_20_ISSUE][
                            V20CredFormat.Format.INDY.api
                        ],
                    ),
                    AttachDecorator.data_base64(
                        INDY_CRED, ident=V20CredFormat.Format.INDY.api
                    ),
                )
            )
            (ret_cx_rec, ret_cred_issue) = await self.manager.issue_credential(
                stored_cx_rec, comment=comment
            )

            mock_save.assert_called_once()
            mock_handler.return_value.issue_credential.assert_called_once_with(
                ret_cx_rec
            )

            assert (
                V20CredIssue.deserialize(ret_cx_rec.cred_issue).attachment()
                == INDY_CRED
            )
            assert ret_cred_issue.attachment() == INDY_CRED
            assert ret_cx_rec.state == V20CredExRecord.STATE_ISSUED
            assert ret_cred_issue._thread_id == thread_id

    async def test_issue_credential_x_no_formats(self):
        comment = "comment"

        cred_request = V20CredRequest(
            formats=[],
            requests_attach=[],
        )

        cx_rec = V20CredExRecord(
            cred_ex_id="dummy-cxid",
            role=V20CredExRecord.ROLE_ISSUER,
            state=V20CredExRecord.STATE_REQUEST_RECEIVED,
            cred_request=cred_request.serialize(),
        )

        with self.assertRaises(V20CredManagerError) as context:
            await self.manager.issue_credential(
                cred_ex_record=cx_rec,
                comment=comment,
            )
        assert "No supported formats" in str(context.exception)

    async def test_issue_credential_existing_cred(self):
        stored_cx_rec = V20CredExRecord(
            state=V20CredExRecord.STATE_REQUEST_RECEIVED,
            cred_issue=async_mock.MagicMock(),
        )

        with self.assertRaises(V20CredManagerError) as context:
            await self.manager.issue_credential(stored_cx_rec)
        assert "called multiple times" in str(context.exception)

    async def test_issue_credential_request_bad_state(self):
        stored_cx_rec = V20CredExRecord(
            state=V20CredExRecord.STATE_PROPOSAL_SENT,
        )

        with self.assertRaises(V20CredManagerError) as context:
            await self.manager.issue_credential(stored_cx_rec)
        assert " state " in str(context.exception)

    async def test_receive_cred(self):
        connection_id = "test_conn_id"

        cred_request = V20CredRequest(
            formats=[
                V20CredFormat(
                    attach_id="0",
                    format_=ATTACHMENT_FORMAT[CRED_20_REQUEST][
                        V20CredFormat.Format.INDY.api
                    ],
                )
            ],
            requests_attach=[AttachDecorator.data_base64(INDY_CRED_REQ, ident="0")],
        )

        stored_cx_rec = V20CredExRecord(
            cred_ex_id="dummy-cxid",
            connection_id=connection_id,
            initiator=V20CredExRecord.INITIATOR_EXTERNAL,
            cred_request=cred_request.serialize(),
            role=V20CredExRecord.ROLE_ISSUER,
        )

        cred_issue = V20CredIssue(
            formats=[
                V20CredFormat(
                    attach_id="0",
                    format_=ATTACHMENT_FORMAT[CRED_20_ISSUE][
                        V20CredFormat.Format.INDY.api
                    ],
                )
            ],
            credentials_attach=[AttachDecorator.data_base64(INDY_CRED, ident="0")],
        )

        with async_mock.patch.object(
            V20CredExRecord, "save", autospec=True
        ) as mock_save, async_mock.patch.object(
            V20CredExRecord,
            "retrieve_by_conn_and_thread",
            async_mock.CoroutineMock(),
        ) as mock_retrieve, async_mock.patch.object(
            V20CredFormat.Format, "handler"
        ) as mock_handler:

            mock_handler.return_value.receive_credential = async_mock.CoroutineMock()
            mock_retrieve.return_value = stored_cx_rec
            ret_cx_rec = await self.manager.receive_credential(
                cred_issue,
                connection_id,
            )

            mock_retrieve.assert_called_once_with(
                self.session, connection_id, cred_issue._thread_id
            )
            mock_save.assert_called_once()
            mock_handler.return_value.receive_credential.assert_called_once_with(
                ret_cx_rec, cred_issue
            )
            assert (
                V20CredIssue.deserialize(ret_cx_rec.cred_issue).attachment()
                == INDY_CRED
            )
            assert ret_cx_rec.state == V20CredExRecord.STATE_CREDENTIAL_RECEIVED

    async def test_receive_cred_x_extra_formats(self):
        connection_id = "test_conn_id"

        cred_request = V20CredRequest(
            formats=[
                V20CredFormat(
                    attach_id="0",
                    format_=ATTACHMENT_FORMAT[CRED_20_REQUEST][
                        V20CredFormat.Format.INDY.api
                    ],
                )
            ],
            requests_attach=[AttachDecorator.data_base64(INDY_CRED_REQ, ident="0")],
        )

        stored_cx_rec = V20CredExRecord(
            cred_ex_id="dummy-cxid",
            connection_id=connection_id,
            initiator=V20CredExRecord.INITIATOR_EXTERNAL,
            cred_request=cred_request.serialize(),
            role=V20CredExRecord.ROLE_ISSUER,
        )

        cred_issue = V20CredIssue(
            formats=[
                V20CredFormat(
                    attach_id="0",
                    format_=ATTACHMENT_FORMAT[CRED_20_ISSUE][
                        V20CredFormat.Format.INDY.api
                    ],
                ),
                V20CredFormat(
                    attach_id="1",
                    format_=ATTACHMENT_FORMAT[CRED_20_ISSUE][
                        V20CredFormat.Format.LD_PROOF.api
                    ],
                ),
            ],
            credentials_attach=[AttachDecorator.data_base64(LD_PROOF_VC, ident="1")],
        )

        with async_mock.patch.object(
            V20CredExRecord,
            "retrieve_by_conn_and_thread",
            async_mock.CoroutineMock(),
        ) as mock_retrieve:
            mock_retrieve.return_value = stored_cx_rec

            with self.assertRaises(V20CredManagerError) as context:
                await self.manager.receive_credential(
                    cred_issue,
                    connection_id,
                )
            assert (
                "Received issue credential format(s) not present in credential"
                in str(context.exception)
            )

    async def test_receive_cred_x_no_formats(self):
        connection_id = "test_conn_id"

        cred_request = V20CredRequest(
            formats=[V20CredFormat(attach_id="0", format_="random")],
            requests_attach=[AttachDecorator.data_base64(INDY_CRED_REQ, ident="0")],
        )

        stored_cx_rec = V20CredExRecord(
            cred_ex_id="dummy-cxid",
            connection_id=connection_id,
            initiator=V20CredExRecord.INITIATOR_EXTERNAL,
            cred_request=cred_request.serialize(),
            role=V20CredExRecord.ROLE_ISSUER,
        )

        cred_issue = V20CredIssue(
            formats=[V20CredFormat(attach_id="0", format_="random")],
            credentials_attach=[AttachDecorator.data_base64(LD_PROOF_VC, ident="0")],
        )

        with async_mock.patch.object(
            V20CredExRecord,
            "retrieve_by_conn_and_thread",
            async_mock.CoroutineMock(),
        ) as mock_retrieve:
            mock_retrieve.return_value = stored_cx_rec

            with self.assertRaises(V20CredManagerError) as context:
                await self.manager.receive_credential(
                    cred_issue,
                    connection_id,
                )
            assert "No supported credential formats received." in str(context.exception)

    async def test_store_credential(self):
        connection_id = "test_conn_id"
        thread_id = "thread-id"
        cred_issue = V20CredIssue(
            formats=[
                V20CredFormat(
                    attach_id="0",
                    format_=ATTACHMENT_FORMAT[CRED_20_ISSUE][
                        V20CredFormat.Format.INDY.api
                    ],
                )
            ],
            credentials_attach=[AttachDecorator.data_base64(INDY_CRED, ident="0")],
        )
        cred_id = "cred_id"

        stored_cx_rec = V20CredExRecord(
            cred_ex_id="dummy-cxid",
            connection_id=connection_id,
            cred_issue=cred_issue.serialize(),
            initiator=V20CredExRecord.INITIATOR_EXTERNAL,
            role=V20CredExRecord.ROLE_ISSUER,
            state=V20CredExRecord.STATE_CREDENTIAL_RECEIVED,
            auto_remove=True,
            thread_id=thread_id,
        )

        with async_mock.patch.object(
            V20CredExRecord, "save", autospec=True
        ) as mock_save, async_mock.patch.object(
            test_module.V20CredManager, "delete_cred_ex_record", autospec=True
        ) as mock_delete, async_mock.patch.object(
            V20CredFormat.Format, "handler"
        ) as mock_handler:

            mock_handler.return_value.store_credential = async_mock.CoroutineMock()

            ret_cx_rec = await self.manager.store_credential(
                stored_cx_rec, cred_id=cred_id
            )

            mock_handler.return_value.store_credential.assert_called_once_with(
                ret_cx_rec, cred_id
            )

            assert (
                V20CredIssue.deserialize(ret_cx_rec.cred_issue).attachment()
                == INDY_CRED
            )
            assert ret_cx_rec.state == V20CredExRecord.STATE_CREDENTIAL_RECEIVED

    async def test_store_credential_bad_state(self):
        thread_id = "thread-id"
        cred_id = "cred-id"

        stored_cx_rec = V20CredExRecord(
            cred_ex_id="dummy-cxid",
            state=V20CredExRecord.STATE_OFFER_RECEIVED,
            thread_id=thread_id,
        )

        with self.assertRaises(V20CredManagerError) as context:
            await self.manager.store_credential(stored_cx_rec, cred_id=cred_id)
        assert " state " in str(context.exception)

    async def test_send_cred_ack(self):
        connection_id = "connection-id"
        stored_exchange = V20CredExRecord(
            cred_ex_id="dummy-cxid",
            connection_id=connection_id,
            initiator=V20CredExRecord.INITIATOR_SELF,
            thread_id="thid",
            parent_thread_id="pthid",
            role=V20CredExRecord.ROLE_ISSUER,
            trace=False,
            auto_remove=True,
        )

        with async_mock.patch.object(
            V20CredExRecord, "save", autospec=True
        ) as mock_save_ex, async_mock.patch.object(
            V20CredExRecord, "delete_record", autospec=True
        ) as mock_delete_ex, async_mock.patch.object(
            test_module.LOGGER, "exception", async_mock.MagicMock()
        ) as mock_log_exception, async_mock.patch.object(
            test_module.LOGGER, "warning", async_mock.MagicMock()
        ) as mock_log_warning:
            mock_delete_ex.side_effect = test_module.StorageError()
            (_, ack) = await self.manager.send_cred_ack(stored_exchange)
            assert ack._thread
            mock_log_exception.assert_called_once()  # cover exception log-and-continue
            mock_log_warning.assert_called_once()  # no BaseResponder

            mock_responder = MockResponder()  # cover with responder
            self.context.injector.bind_instance(BaseResponder, mock_responder)
            (cx_rec, ack) = await self.manager.send_cred_ack(stored_exchange)
            assert ack._thread
            assert cx_rec.state == V20CredExRecord.STATE_DONE

    async def test_receive_cred_ack(self):
        connection_id = "conn-id"
        stored_cx_rec = V20CredExRecord(
            cred_ex_id="dummy-cxid",
            connection_id=connection_id,
            initiator=V20CredExRecord.INITIATOR_SELF,
            role=V20CredExRecord.ROLE_ISSUER,
        )

        ack = V20CredAck()

        with async_mock.patch.object(
            V20CredExRecord, "save", autospec=True
        ) as mock_save, async_mock.patch.object(
            V20CredExRecord, "delete_record", autospec=True
        ) as mock_delete, async_mock.patch.object(
            V20CredExRecord, "retrieve_by_conn_and_thread", async_mock.CoroutineMock()
        ) as mock_retrieve, async_mock.patch.object(
            test_module.V20CredManager, "delete_cred_ex_record", autospec=True
        ) as mock_delete:
            mock_retrieve.return_value = stored_cx_rec
            ret_cx_rec = await self.manager.receive_credential_ack(
                ack,
                connection_id,
            )

            mock_retrieve.assert_called_once_with(
                self.session,
                connection_id,
                ack._thread_id,
            )
            mock_save.assert_called_once()

            assert ret_cx_rec.state == V20CredExRecord.STATE_DONE
            mock_delete.assert_called_once()

    async def test_delete_cred_ex_record(self):
        stored_cx_rec = async_mock.MagicMock(delete_record=async_mock.CoroutineMock())
        stored_indy = async_mock.MagicMock(delete_record=async_mock.CoroutineMock())

        with async_mock.patch.object(
            V20CredExRecord, "delete_record", autospec=True
        ) as mock_delete, async_mock.patch.object(
            V20CredExRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_retrieve, async_mock.patch.object(
            test_module, "V20CredFormat", async_mock.MagicMock()
        ) as mock_cred_format:
            mock_retrieve.return_value = stored_cx_rec
            mock_cred_format.Format = [
                async_mock.MagicMock(
                    detail=async_mock.MagicMock(
                        query_by_cred_ex_id=async_mock.CoroutineMock(
                            return_value=[
                                stored_indy,
                                stored_indy,
                            ]  # deletion should get all, although there oughn't be >1
                        )
                    )
                ),
                async_mock.MagicMock(
                    detail=async_mock.MagicMock(
                        query_by_cred_ex_id=async_mock.CoroutineMock(return_value=[])
                    )
                ),
            ]
            await self.manager.delete_cred_ex_record("dummy")

    async def test_create_problem_report(self):
        connection_id = "connection-id"
        stored_exchange = V20CredExRecord(
            cred_ex_id="dummy-cxid",
            conn_id=connection_id,
            initiator=V20CredExRecord.INITIATOR_SELF,
            role=V20CredExRecord.ROLE_ISSUER,
            state=V20CredExRecord.STATE_REQUEST_RECEIVED,
            thread_id="dummy-thid",
        )

        with async_mock.patch.object(V20CredExRecord, "save", autospec=True) as save_ex:
            report = await self.manager.create_problem_report(
                stored_exchange,
                "The front fell off",
            )

        assert stored_exchange.state is None
        assert report._thread_id == stored_exchange.thread_id

    async def test_receive_problem_report(self):
        connection_id = "connection-id"
        stored_exchange = V20CredExRecord(
            cred_ex_id="dummy-cxid",
            connection_id=connection_id,
            initiator=V20CredExRecord.INITIATOR_SELF,
            role=V20CredExRecord.ROLE_ISSUER,
        )
        problem = V20CredProblemReport(
            description={
                "code": test_module.ProblemReportReason.ISSUANCE_ABANDONED.value,
                "en": "Insufficient privilege",
            }
        )

        with async_mock.patch.object(
            V20CredExRecord, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            V20CredExRecord,
            "retrieve_by_conn_and_thread",
            async_mock.CoroutineMock(),
        ) as retrieve_ex:
            retrieve_ex.return_value = stored_exchange

            ret_exchange = await self.manager.receive_problem_report(
                problem, connection_id
            )
            retrieve_ex.assert_called_once_with(
                self.session, connection_id, problem._thread_id
            )
            save_ex.assert_called_once()

            assert ret_exchange.state is None

    async def test_receive_problem_report_x(self):
        connection_id = "connection-id"
        stored_exchange = V20CredExRecord(
            cred_ex_id="dummy-cxid",
            initiator=V20CredExRecord.INITIATOR_SELF,
            role=V20CredExRecord.ROLE_ISSUER,
            state=V20CredExRecord.STATE_REQUEST_RECEIVED,
        )
        problem = V20CredProblemReport(
            description={
                "code": test_module.ProblemReportReason.ISSUANCE_ABANDONED.value,
                "en": "Insufficient privilege",
            }
        )

        with async_mock.patch.object(
            V20CredExRecord,
            "retrieve_by_conn_and_thread",
            async_mock.CoroutineMock(),
        ) as retrieve_ex:
            retrieve_ex.side_effect = test_module.StorageNotFoundError("No such record")

            with self.assertRaises(test_module.StorageNotFoundError):
                await self.manager.receive_problem_report(problem, connection_id)

    async def test_retrieve_records(self):
        self.cache = InMemoryCache()
        self.session.context.injector.bind_instance(BaseCache, self.cache)

        for index in range(2):
            cx_rec = V20CredExRecord(
                connection_id=str(index),
                thread_id=str(1000 + index),
                initiator=V20CredExRecord.INITIATOR_SELF,
                role=V20CredExRecord.ROLE_ISSUER,
            )

            await cx_rec.save(self.session)

        for i in range(2):  # second pass gets from cache
            for index in range(2):
                ret_ex = await V20CredExRecord.retrieve_by_conn_and_thread(
                    self.session, str(index), str(1000 + index)
                )
                assert ret_ex.connection_id == str(index)
                assert ret_ex.thread_id == str(1000 + index)
