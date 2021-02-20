import asyncio
import json

from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock
from copy import deepcopy
from time import time

from .....core.in_memory import InMemoryProfile
from .....cache.base import BaseCache
from .....cache.in_memory import InMemoryCache
from .....indy.holder import IndyHolder
from .....indy.issuer import IndyIssuer
from .....messaging.credential_definitions.util import CRED_DEF_SENT_RECORD_TYPE
from .....messaging.decorators.attach_decorator import AttachDecorator
from .....ledger.base import BaseLedger
from .....storage.base import StorageRecord
from .....storage.error import StorageNotFoundError

from .. import manager as test_module
from ..manager import V20CredManager, V20CredManagerError
from ..messages.cred_ack import V20CredAck
from ..messages.cred_issue import V20CredIssue
from ..messages.cred_format import V20CredFormat
from ..messages.cred_offer import V20CredOffer
from ..messages.cred_proposal import V20CredProposal
from ..messages.cred_request import V20CredRequest
from ..messages.inner.cred_preview import V20CredPreview, V20CredAttrSpec
from ..models.cred_ex_record import V20CredExRecord
from ..models.detail.dif import V20CredExRecordDIF
from ..models.detail.indy import V20CredExRecordIndy


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
                "jurisdictionId": "...",
                "incorporationDate": "...",
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

    async def test_get_indy_detail_record(self):
        cred_ex_id = "dummy"
        detail_indy = V20CredExRecordIndy(
            cred_ex_id=cred_ex_id,
            rev_reg_id="rr-id",
            cred_rev_id="0",
        )
        await detail_indy.save(self.session)
        assert (
            await self.manager.get_detail_record(cred_ex_id, V20CredFormat.Format.INDY)
            == detail_indy
        )
        assert (
            await self.manager.get_detail_record(cred_ex_id, V20CredFormat.Format.DIF)
            is None
        )

    async def test_get_dif_detail_record(self):
        cred_ex_id = "dummy"
        detail_dif = V20CredExRecordDIF(cred_ex_id=cred_ex_id, item="my-item")
        await detail_dif.save(self.session)
        await self.manager.get_detail_record(cred_ex_id, V20CredFormat.Format.DIF)

    async def test_prepare_send(self):
        conn_id = "test_conn_id"
        cred_preview = V20CredPreview(
            attributes=(
                V20CredAttrSpec(name="legalName", value="value"),
                V20CredAttrSpec(name="jurisdictionId", value="value"),
                V20CredAttrSpec(name="incorporationDate", value="value"),
            )
        )
        cred_proposal = V20CredProposal(
            credential_preview=cred_preview,
            formats=[V20CredFormat(attach_id="0", format_=V20CredFormat.Format.INDY)],
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
                conn_id, cred_proposal
            )
            create_offer.assert_called_once()
            assert ret_cred_ex_rec is create_offer.return_value[0]
            arg_cred_ex_rec = create_offer.call_args[1]["cred_ex_record"]
            assert arg_cred_ex_rec.auto_issue
            assert arg_cred_ex_rec.conn_id == conn_id
            assert arg_cred_ex_rec.role == V20CredExRecord.ROLE_ISSUER
            assert arg_cred_ex_rec.cred_proposal == cred_proposal.serialize()

    async def test_create_proposal(self):
        conn_id = "test_conn_id"
        comment = "comment"
        cred_preview = V20CredPreview(
            attributes=(
                V20CredAttrSpec(name="legalName", value="value"),
                V20CredAttrSpec(name="jurisdictionId", value="value"),
                V20CredAttrSpec(name="incorporationDate", value="value"),
            )
        )

        self.ledger.credential_definition_id2schema_id = async_mock.CoroutineMock(
            return_value=SCHEMA_ID
        )

        with async_mock.patch.object(
            V20CredExRecord, "save", autospec=True
        ) as mock_save:
            cx_rec = await self.manager.create_proposal(
                conn_id,
                comment=comment,
                cred_preview=cred_preview,
                fmt2filter={V20CredFormat.Format.INDY: None},
            )  # leave underspecified until offer receipt
            mock_save.assert_called_once()

        cred_proposal = V20CredProposal.deserialize(cx_rec.cred_proposal)
        assert not cred_proposal.filter(
            V20CredFormat.Format.INDY
        ).keys()  # leave underspecified until offer receipt
        assert cx_rec.conn_id == conn_id
        assert cx_rec.thread_id == cred_proposal._thread_id
        assert cx_rec.role == V20CredExRecord.ROLE_HOLDER
        assert cx_rec.state == V20CredExRecord.STATE_PROPOSAL_SENT
        assert cx_rec.cred_preview == cred_preview.serialize()

    async def test_create_proposal_no_preview(self):
        conn_id = "test_conn_id"
        comment = "comment"

        self.ledger.credential_definition_id2schema_id = async_mock.CoroutineMock(
            return_value=SCHEMA_ID
        )

        with async_mock.patch.object(
            V20CredExRecord, "save", autospec=True
        ) as mock_save:
            cx_rec = await self.manager.create_proposal(
                conn_id,
                comment=comment,
                cred_preview=None,
                fmt2filter={V20CredFormat.Format.INDY: {"cred_def_id": CRED_DEF_ID}},
            )
            mock_save.assert_called_once()

        cred_proposal = V20CredProposal.deserialize(cx_rec.cred_proposal)
        assert cred_proposal.filter(V20CredFormat.Format.INDY) == {
            "cred_def_id": CRED_DEF_ID
        }
        assert cx_rec.conn_id == conn_id
        assert cx_rec.thread_id == cred_proposal._thread_id
        assert cx_rec.role == V20CredExRecord.ROLE_HOLDER
        assert cx_rec.state == V20CredExRecord.STATE_PROPOSAL_SENT

    async def test_receive_proposal(self):
        conn_id = "test_conn_id"

        cred_preview = V20CredPreview(
            attributes=(
                V20CredAttrSpec(name="legalName", value="value"),
                V20CredAttrSpec(name="jurisdictionId", value="value"),
                V20CredAttrSpec(name="incorporationDate", value="value"),
            )
        )

        with async_mock.patch.object(
            V20CredExRecord, "save", autospec=True
        ) as mock_save:
            cred_proposal = V20CredProposal(
                credential_preview=cred_preview,
                formats=[
                    V20CredFormat(attach_id="0", format_=V20CredFormat.Format.INDY)
                ],
                filters_attach=[
                    AttachDecorator.data_base64({"cred_def_id": CRED_DEF_ID}, ident="0")
                ],
            )

            cx_rec = await self.manager.receive_proposal(cred_proposal, conn_id)
            mock_save.assert_called_once()

            ret_cred_proposal = V20CredProposal.deserialize(cx_rec.cred_proposal)

            assert ret_cred_proposal.filter(V20CredFormat.Format.INDY) == {
                "cred_def_id": CRED_DEF_ID
            }
            assert (
                ret_cred_proposal.credential_preview.attributes
                == cred_preview.attributes
            )
            assert cx_rec.conn_id == conn_id
            assert cx_rec.role == V20CredExRecord.ROLE_ISSUER
            assert cx_rec.state == V20CredExRecord.STATE_PROPOSAL_RECEIVED
            assert cx_rec.thread_id == cred_proposal._thread_id

    async def test_create_free_offer(self):
        comment = "comment"
        schema_id_parts = SCHEMA_ID.split(":")

        cred_preview = V20CredPreview(
            attributes=(
                V20CredAttrSpec(name="legalName", value="value"),
                V20CredAttrSpec(name="jurisdictionId", value="value"),
                V20CredAttrSpec(name="incorporationDate", value="value"),
            )
        )
        cred_proposal = V20CredProposal(
            credential_preview=cred_preview,
            formats=[V20CredFormat(attach_id="0", format_=V20CredFormat.Format.INDY)],
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
        ) as mock_save:
            self.cache = InMemoryCache()
            self.context.injector.bind_instance(BaseCache, self.cache)

            indy_offer = {
                "schema_id": SCHEMA_ID,
                "cred_def_id": CRED_DEF_ID,
                "nonce": "0",
                "...": "...",
            }

            issuer = async_mock.MagicMock(IndyIssuer, autospec=True)
            issuer.create_credential_offer = async_mock.CoroutineMock(
                return_value=json.dumps(indy_offer)
            )
            self.context.injector.bind_instance(IndyIssuer, issuer)

            cred_def_record = StorageRecord(
                CRED_DEF_SENT_RECORD_TYPE,
                CRED_DEF_ID,
                {
                    "schema_id": SCHEMA_ID,
                    "schema_issuer_did": schema_id_parts[0],
                    "schema_name": schema_id_parts[-2],
                    "schema_version": schema_id_parts[-1],
                    "issuer_did": TEST_DID,
                    "cred_def_id": CRED_DEF_ID,
                    "epoch": str(int(time())),
                },
            )
            await self.session.storage.add_record(cred_def_record)

            (ret_cx_rec, ret_offer) = await self.manager.create_offer(
                cred_ex_record=cx_rec,
                replacement_id="0",
                comment=comment,
            )
            assert ret_cx_rec == cx_rec
            mock_save.assert_called_once()

            issuer.create_credential_offer.assert_called_once_with(CRED_DEF_ID)

            assert cx_rec.cred_ex_id == ret_cx_rec._id  # cover property
            assert cx_rec.thread_id == ret_offer._thread_id
            assert cx_rec.role == V20CredExRecord.ROLE_ISSUER
            assert cx_rec.state == V20CredExRecord.STATE_OFFER_SENT
            assert (
                V20CredOffer.deserialize(cx_rec.cred_offer).offer(
                    V20CredFormat.Format.INDY
                )
                == indy_offer
            )

            await self.manager.create_offer(
                cred_ex_record=cx_rec,
                replacement_id="0",
                comment=comment,
            )  # once more to cover case where offer is available in cache

    async def test_create_free_offer_attr_mismatch(self):
        comment = "comment"
        schema_id_parts = SCHEMA_ID.split(":")

        cred_preview = V20CredPreview(
            attributes=(  # names have spaces instead of camel case
                V20CredAttrSpec(name="legal name", value="value"),
                V20CredAttrSpec(name="jurisdiction id", value="value"),
                V20CredAttrSpec(name="incorporation date", value="value"),
            )
        )
        cred_proposal = V20CredProposal(
            credential_preview=cred_preview,
            formats=[V20CredFormat(attach_id="0", format_=V20CredFormat.Format.INDY)],
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
        ) as mock_mock_save:
            self.cache = InMemoryCache()
            self.context.injector.bind_instance(BaseCache, self.cache)

            indy_offer = {
                "schema_id": SCHEMA_ID,
                "cred_def_id": CRED_DEF_ID,
                "nonce": "0",
                "...": "...",
            }

            issuer = async_mock.MagicMock(IndyIssuer, autospec=True)
            issuer.create_credential_offer = async_mock.CoroutineMock(
                return_value=json.dumps(indy_offer)
            )
            self.context.injector.bind_instance(IndyIssuer, issuer)

            cred_def_record = StorageRecord(
                CRED_DEF_SENT_RECORD_TYPE,
                CRED_DEF_ID,
                {
                    "schema_id": SCHEMA_ID,
                    "schema_issuer_did": schema_id_parts[0],
                    "schema_name": schema_id_parts[-2],
                    "schema_version": schema_id_parts[-1],
                    "issuer_did": TEST_DID,
                    "cred_def_id": CRED_DEF_ID,
                    "epoch": str(int(time())),
                },
            )
            await self.session.storage.add_record(cred_def_record)

            with self.assertRaises(V20CredManagerError):
                await self.manager.create_offer(
                    cred_ex_record=cx_rec,
                    replacement_id="0",
                    comment=comment,
                )

    async def test_create_bound_offer(self):
        TEST_DID = "LjgpST2rjsoxYegQDRm7EL"
        schema_id_parts = SCHEMA_ID.split(":")
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
            formats=[V20CredFormat(attach_id="0", format_=V20CredFormat.Format.INDY)],
            filters_attach=[AttachDecorator.data_base64({}, ident="0")],
        )
        cx_rec = V20CredExRecord(
            cred_ex_id="dummy-cxid",
            role=V20CredExRecord.ROLE_ISSUER,
            cred_proposal=cred_proposal.serialize(),
        )

        with async_mock.patch.object(
            V20CredExRecord, "save", autospec=True
        ) as mock_save, async_mock.patch.object(
            V20CredExRecord, "get_cached_key", autospec=True
        ) as get_cached_key, async_mock.patch.object(
            V20CredExRecord, "set_cached_key", autospec=True
        ) as set_cached_key:
            get_cached_key.return_value = None

            indy_offer = {
                "schema_id": SCHEMA_ID,
                "cred_def_id": CRED_DEF_ID,
                "nonce": "0",
                "...": "...",
            }

            issuer = async_mock.MagicMock(IndyIssuer, autospec=True)
            issuer.create_credential_offer = async_mock.CoroutineMock(
                return_value=json.dumps(indy_offer)
            )
            self.context.injector.bind_instance(IndyIssuer, issuer)

            cred_def_record = StorageRecord(
                CRED_DEF_SENT_RECORD_TYPE,
                CRED_DEF_ID,
                {
                    "schema_id": SCHEMA_ID,
                    "schema_issuer_did": schema_id_parts[0],
                    "schema_name": schema_id_parts[-2],
                    "schema_version": schema_id_parts[-1],
                    "issuer_did": TEST_DID,
                    "cred_def_id": CRED_DEF_ID,
                    "epoch": str(int(time())),
                },
            )
            await self.session.storage.add_record(cred_def_record)

            (ret_cx_rec, ret_offer) = await self.manager.create_offer(
                cred_ex_record=cx_rec, comment=comment
            )
            assert ret_cx_rec == cx_rec
            mock_save.assert_called_once()

            issuer.create_credential_offer.assert_called_once_with(CRED_DEF_ID)

            assert cx_rec.thread_id == ret_offer._thread_id
            assert cx_rec.role == V20CredExRecord.ROLE_ISSUER
            assert cx_rec.state == V20CredExRecord.STATE_OFFER_SENT
            assert (
                V20CredOffer.deserialize(cx_rec.cred_offer).offer(
                    V20CredFormat.Format.INDY
                )
                == indy_offer
            )

            # additionally check that manager passed credential preview through
            assert ret_offer.credential_preview.attributes == cred_preview.attributes

    async def test_create_bound_offer_no_matching_sent_cred_def(self):
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
            formats=[V20CredFormat(attach_id="0", format_=V20CredFormat.Format.INDY)],
            filters_attach=[AttachDecorator.data_base64({}, ident="0")],
        )
        cx_rec = V20CredExRecord(
            cred_ex_id="dummy-cxid",
            role=V20CredExRecord.ROLE_ISSUER,
            cred_proposal=cred_proposal.serialize(),
        )

        with async_mock.patch.object(
            V20CredExRecord, "save", autospec=True
        ) as mock_save, async_mock.patch.object(
            V20CredExRecord, "get_cached_key", autospec=True
        ) as get_cached_key, async_mock.patch.object(
            V20CredExRecord, "set_cached_key", autospec=True
        ) as set_cached_key:
            get_cached_key.return_value = None
            indy_offer = {
                "schema_id": SCHEMA_ID,
                "cred_def_id": CRED_DEF_ID,
                "nonce": "0",
                "...": "...",
            }
            issuer = async_mock.MagicMock()
            issuer.create_credential_offer = async_mock.CoroutineMock(
                return_value=indy_offer
            )
            self.context.injector.bind_instance(IndyIssuer, issuer)

            with self.assertRaises(V20CredManagerError) as context:
                await self.manager.create_offer(cred_ex_record=cx_rec, comment=comment)
            assert "Issuer has no operable cred def" in str(context.exception)

    async def test_receive_offer_proposed(self):
        conn_id = "test_conn_id"
        indy_offer = {
            "schema_id": SCHEMA_ID,
            "cred_def_id": CRED_DEF_ID,
            "nonce": "0",
            "...": "...",
        }
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
            formats=[V20CredFormat(attach_id="0", format_=V20CredFormat.Format.INDY)],
            filters_attach=[AttachDecorator.data_base64({}, ident="0")],
        )
        cred_offer = V20CredOffer(
            credential_preview=cred_preview,
            formats=[V20CredFormat(attach_id="0", format_=V20CredFormat.Format.INDY)],
            offers_attach=[AttachDecorator.data_base64(indy_offer, ident="0")],
        )
        cred_offer.assign_thread_id(thread_id)

        stored_cx_rec = V20CredExRecord(
            cred_ex_id="dummy-cxid",
            conn_id=conn_id,
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
        ) as mock_retrieve:
            cx_rec = await self.manager.receive_offer(cred_offer, conn_id)

            assert cx_rec.conn_id == conn_id
            assert cx_rec.thread_id == cred_offer._thread_id
            assert cx_rec.role == V20CredExRecord.ROLE_HOLDER
            assert cx_rec.state == V20CredExRecord.STATE_OFFER_RECEIVED
            assert (
                V20CredOffer.deserialize(cx_rec.cred_offer).offer(
                    V20CredFormat.Format.INDY
                )
                == indy_offer
            )
            assert (
                V20CredProposal.deserialize(
                    cx_rec.cred_proposal
                ).credential_preview.attributes
                == cred_preview.attributes
            )

    async def test_receive_free_offer(self):
        conn_id = "test_conn_id"
        indy_offer = {
            "schema_id": SCHEMA_ID,
            "cred_def_id": CRED_DEF_ID,
            "nonce": "0",
            "...": "...",
        }
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
            formats=[V20CredFormat(attach_id="0", format_=V20CredFormat.Format.INDY)],
            offers_attach=[AttachDecorator.data_base64(indy_offer, ident="0")],
        )
        cred_offer.assign_thread_id(thread_id)

        self.context.message = cred_offer
        self.context.conn_record = async_mock.MagicMock()
        self.context.conn_record.conn_id = conn_id

        with async_mock.patch.object(
            V20CredExRecord, "save", autospec=True
        ) as mock_save, async_mock.patch.object(
            V20CredExRecord, "retrieve_by_conn_and_thread", async_mock.CoroutineMock()
        ) as mock_retrieve:
            mock_retrieve.side_effect = (StorageNotFoundError(),)
            cx_rec = await self.manager.receive_offer(cred_offer, conn_id)

            assert cx_rec.conn_id == conn_id
            assert cx_rec.thread_id == cred_offer._thread_id
            assert cx_rec.role == V20CredExRecord.ROLE_HOLDER
            assert cx_rec.state == V20CredExRecord.STATE_OFFER_RECEIVED
            assert (
                V20CredOffer.deserialize(cx_rec.cred_offer).offer(
                    V20CredFormat.Format.INDY
                )
                == indy_offer
            )
            assert (
                V20CredProposal.deserialize(
                    cx_rec.cred_proposal
                ).credential_preview.attributes
                == cred_preview.attributes
            )

    async def test_create_request(self):
        conn_id = "test_conn_id"
        nonce = "0"
        indy_offer = {
            "schema_id": SCHEMA_ID,
            "cred_def_id": CRED_DEF_ID,
            "nonce": nonce,
            "...": "...",
        }
        indy_cred_req = {
            "schema_id": SCHEMA_ID,
            "cred_def_id": CRED_DEF_ID,
            "...": "...",
        }
        thread_id = "thread-id"
        holder_did = "did"

        cred_offer = V20CredOffer(
            formats=[V20CredFormat(attach_id="0", format_=V20CredFormat.Format.INDY)],
            offers_attach=[AttachDecorator.data_base64(indy_offer, ident="0")],
        )
        cred_offer.assign_thread_id(thread_id)

        stored_cx_rec = V20CredExRecord(
            cred_ex_id="dummy-cxid",
            conn_id=conn_id,
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
        ) as mock_save:
            cred_def = {"cred": "def"}
            self.ledger.get_credential_definition = async_mock.CoroutineMock(
                return_value=cred_def
            )

            cred_req_meta = {}
            holder = async_mock.MagicMock()
            holder.create_credential_request = async_mock.CoroutineMock(
                return_value=(json.dumps(indy_cred_req), json.dumps(cred_req_meta))
            )
            self.context.injector.bind_instance(IndyHolder, holder)

            ret_cx_rec, ret_cred_req = await self.manager.create_request(
                stored_cx_rec, holder_did
            )

            holder.create_credential_request.assert_called_once_with(
                indy_offer, cred_def, holder_did
            )

            assert ret_cred_req.cred_request() == indy_cred_req
            assert ret_cred_req._thread_id == thread_id

            assert ret_cx_rec.state == V20CredExRecord.STATE_REQUEST_SENT

            # cover case with request in cache
            stored_cx_rec.cred_request = None
            stored_cx_rec.state = V20CredExRecord.STATE_OFFER_RECEIVED
            await self.manager.create_request(stored_cx_rec, holder_did)

            # cover case with existing cred req
            stored_cx_rec.state = V20CredExRecord.STATE_OFFER_RECEIVED
            stored_cx_rec.cred_request = ret_cred_req
            with self.assertRaises(V20CredManagerError) as context:
                await self.manager.create_request(stored_cx_rec, holder_did)
            assert "called multiple times" in str(context.exception)

    async def test_create_request_no_cache(self):
        conn_id = "test_conn_id"
        nonce = "0"
        indy_offer = {
            "schema_id": SCHEMA_ID,
            "cred_def_id": CRED_DEF_ID,
            "nonce": nonce,
            "...": "...",
        }
        indy_cred_req = {
            "schema_id": SCHEMA_ID,
            "cred_def_id": CRED_DEF_ID,
            "...": "...",
        }
        thread_id = "thread-id"
        holder_did = "did"

        cred_offer = V20CredOffer(
            formats=[V20CredFormat(attach_id="0", format_=V20CredFormat.Format.INDY)],
            offers_attach=[AttachDecorator.data_base64(indy_offer, ident="0")],
        )
        cred_offer.assign_thread_id(thread_id)

        stored_cx_rec = V20CredExRecord(
            cred_ex_id="dummy-cxid",
            conn_id=conn_id,
            cred_offer=cred_offer.serialize(),
            initiator=V20CredExRecord.INITIATOR_SELF,
            role=V20CredExRecord.ROLE_HOLDER,
            state=V20CredExRecord.STATE_OFFER_RECEIVED,
            thread_id=thread_id,
        )

        with async_mock.patch.object(
            V20CredExRecord, "save", autospec=True
        ) as mock_save:
            cred_def = {"cred": "def"}
            self.ledger.get_credential_definition = async_mock.CoroutineMock(
                return_value=cred_def
            )

            cred_req_meta = {}
            holder = async_mock.MagicMock()
            holder.create_credential_request = async_mock.CoroutineMock(
                return_value=(json.dumps(indy_cred_req), json.dumps(cred_req_meta))
            )
            self.context.injector.bind_instance(IndyHolder, holder)

            ret_cx_rec, ret_cred_request = await self.manager.create_request(
                stored_cx_rec, holder_did
            )

            holder.create_credential_request.assert_called_once_with(
                indy_offer, cred_def, holder_did
            )

            assert ret_cred_request.cred_request() == indy_cred_req
            assert ret_cred_request._thread_id == thread_id

            assert ret_cx_rec.state == V20CredExRecord.STATE_REQUEST_SENT

    async def test_create_request_bad_state(self):
        conn_id = "test_conn_id"
        indy_offer = {
            "schema_id": SCHEMA_ID,
            "cred_def_id": CRED_DEF_ID,
            "nonce": "0",
            "...": "...",
        }
        thread_id = "thread-id"
        holder_did = "did"

        cred_offer = V20CredOffer(
            formats=[V20CredFormat(attach_id="0", format_=V20CredFormat.Format.INDY)],
            offers_attach=[AttachDecorator.data_base64(indy_offer, ident="0")],
        )
        cred_offer.assign_thread_id(thread_id)

        stored_cx_rec = V20CredExRecord(
            cred_ex_id="dummy-cxid",
            conn_id=conn_id,
            cred_offer=cred_offer.serialize(),
            initiator=V20CredExRecord.INITIATOR_SELF,
            role=V20CredExRecord.ROLE_HOLDER,
            state=V20CredExRecord.STATE_PROPOSAL_SENT,
            thread_id=thread_id,
        )

        with self.assertRaises(V20CredManagerError) as context:
            await self.manager.create_request(stored_cx_rec, holder_did)
        assert " state " in str(context.exception)

    async def test_create_request_no_offer_nonce(self):
        conn_id = "test_conn_id"
        indy_offer = {"schema_id": SCHEMA_ID, "cred_def_id": CRED_DEF_ID, "...": "..."}
        thread_id = "thread-id"
        holder_did = "did"

        cred_offer = V20CredOffer(
            formats=[V20CredFormat(attach_id="0", format_=V20CredFormat.Format.INDY)],
            offers_attach=[AttachDecorator.data_base64(indy_offer, ident="0")],
        )
        cred_offer.assign_thread_id(thread_id)

        stored_cx_rec = V20CredExRecord(
            cred_ex_id="dummy-cxid",
            conn_id=conn_id,
            cred_offer=cred_offer.serialize(),
            initiator=V20CredExRecord.INITIATOR_SELF,
            role=V20CredExRecord.ROLE_HOLDER,
            state=V20CredExRecord.STATE_OFFER_RECEIVED,
            thread_id=thread_id,
        )

        with self.assertRaises(V20CredManagerError):
            await self.manager.create_request(stored_cx_rec, holder_did)

    async def test_receive_request(self):
        conn_id = "test_conn_id"
        indy_cred_req = {
            "schema_id": SCHEMA_ID,
            "cred_def_id": CRED_DEF_ID,
            "...": "...",
        }

        stored_cx_rec = V20CredExRecord(
            cred_ex_id="dummy-cxid",
            conn_id=conn_id,
            initiator=V20CredExRecord.INITIATOR_EXTERNAL,
            role=V20CredExRecord.ROLE_ISSUER,
        )

        cred_request = V20CredRequest(
            formats=[V20CredFormat(attach_id="0", format_=V20CredFormat.Format.INDY)],
            requests_attach=[AttachDecorator.data_base64(indy_cred_req, ident="0")],
        )

        with async_mock.patch.object(
            V20CredExRecord, "save", autospec=True
        ) as mock_save, async_mock.patch.object(
            V20CredExRecord, "retrieve_by_conn_and_thread", async_mock.CoroutineMock()
        ) as mock_retrieve:
            mock_retrieve.return_value = stored_cx_rec
            cx_rec = await self.manager.receive_request(cred_request, conn_id)

            mock_retrieve.assert_called_once_with(
                self.session, conn_id, cred_request._thread_id
            )
            mock_save.assert_called_once()

            assert cx_rec.state == V20CredExRecord.STATE_REQUEST_RECEIVED
            assert (
                V20CredRequest.deserialize(cx_rec.cred_request).cred_request()
                == indy_cred_req
            )

    async def test_issue_credential(self):
        conn_id = "test_conn_id"
        comment = "comment"
        attr_values = {
            "legalName": "value",
            "jurisdictionId": "value",
            "incorporationDate": "value",
        }
        indy_offer = {
            "schema_id": SCHEMA_ID,
            "cred_def_id": CRED_DEF_ID,
            "nonce": "0",
            "...": "...",
        }
        indy_cred_req = {
            "schema_id": SCHEMA_ID,
            "cred_def_id": CRED_DEF_ID,
            "...": "...",
        }
        thread_id = "thread-id"

        cred_preview = V20CredPreview(
            attributes=[
                V20CredAttrSpec(name=k, value=v) for (k, v) in attr_values.items()
            ]
        )
        cred_proposal = V20CredProposal(
            credential_preview=cred_preview,
            formats=[V20CredFormat(attach_id="0", format_=V20CredFormat.Format.INDY)],
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
            formats=[V20CredFormat(attach_id="0", format_=V20CredFormat.Format.INDY)],
            offers_attach=[AttachDecorator.data_base64(indy_offer, ident="0")],
        )
        cred_offer.assign_thread_id(thread_id)
        cred_request = V20CredRequest(
            formats=[V20CredFormat(attach_id="0", format_=V20CredFormat.Format.INDY)],
            requests_attach=[AttachDecorator.data_base64(indy_cred_req, ident="0")],
        )

        stored_cx_rec = V20CredExRecord(
            cred_ex_id="dummy-cxid",
            conn_id=conn_id,
            cred_proposal=cred_proposal.serialize(),
            cred_offer=cred_offer.serialize(),
            cred_request=cred_request.serialize(),
            initiator=V20CredExRecord.INITIATOR_SELF,
            role=V20CredExRecord.ROLE_ISSUER,
            state=V20CredExRecord.STATE_REQUEST_RECEIVED,
            thread_id=thread_id,
        )

        issuer = async_mock.MagicMock()
        indy_cred = {"schema_id": SCHEMA_ID, "cred_def_id": CRED_DEF_ID, "...": "..."}
        cred_rev_id = "1000"
        issuer.create_credential = async_mock.CoroutineMock(
            return_value=(json.dumps(indy_cred), cred_rev_id)
        )
        self.context.injector.bind_instance(IndyIssuer, issuer)

        with async_mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as revoc, async_mock.patch.object(
            asyncio, "ensure_future", autospec=True
        ) as asyncio_mock, async_mock.patch.object(
            V20CredExRecord, "save", autospec=True
        ) as mock_save:
            revoc.return_value.get_active_issuer_rev_reg_record = (
                async_mock.CoroutineMock(
                    return_value=async_mock.MagicMock(  # active_rev_reg_rec
                        revoc_reg_id=REV_REG_ID,
                        get_registry=async_mock.CoroutineMock(
                            return_value=async_mock.MagicMock(  # rev_reg
                                tails_local_path="dummy-path",
                                get_or_fetch_local_tails_path=(
                                    async_mock.CoroutineMock()
                                ),
                            )
                        ),
                    )
                )
            )
            (ret_cx_rec, ret_cred_issue) = await self.manager.issue_credential(
                stored_cx_rec, comment=comment, retries=1
            )

            mock_save.assert_called_once()

            issuer.create_credential.assert_called_once_with(
                SCHEMA,
                indy_offer,
                indy_cred_req,
                attr_values,
                stored_cx_rec.cred_ex_id,
                REV_REG_ID,
                "dummy-path",
            )

            assert V20CredIssue.deserialize(ret_cx_rec.cred_issue).cred() == indy_cred
            assert ret_cred_issue.cred() == indy_cred
            assert ret_cx_rec.state == V20CredExRecord.STATE_ISSUED
            assert ret_cred_issue._thread_id == thread_id

            # cover case with existing cred
            stored_cx_rec.state = V20CredExRecord.STATE_REQUEST_RECEIVED
            stored_cx_rec.cred_issue = ret_cred_issue
            with self.assertRaises(V20CredManagerError) as context:
                await self.manager.issue_credential(stored_cx_rec, retries=0)
            assert "called multiple times" in str(context.exception)

    async def test_issue_credential_non_revocable(self):
        CRED_DEF_NR = deepcopy(CRED_DEF)
        CRED_DEF_NR["value"]["revocation"] = None
        conn_id = "test_conn_id"
        comment = "comment"
        attr_values = {
            "legalName": "value",
            "jurisdictionId": "value",
            "incorporationDate": "value",
        }
        indy_offer = {
            "schema_id": SCHEMA_ID,
            "cred_def_id": CRED_DEF_ID,
            "nonce": "0",
            "...": "...",
        }
        indy_cred_req = {
            "schema_id": SCHEMA_ID,
            "cred_def_id": CRED_DEF_ID,
            "...": "...",
        }
        thread_id = "thread-id"

        cred_preview = V20CredPreview(
            attributes=[
                V20CredAttrSpec(name=k, value=v) for (k, v) in attr_values.items()
            ]
        )
        cred_proposal = V20CredProposal(
            credential_preview=cred_preview,
            formats=[V20CredFormat(attach_id="0", format_=V20CredFormat.Format.INDY)],
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
            formats=[V20CredFormat(attach_id="0", format_=V20CredFormat.Format.INDY)],
            offers_attach=[AttachDecorator.data_base64(indy_offer, ident="0")],
        )
        cred_offer.assign_thread_id(thread_id)
        cred_request = V20CredRequest(
            formats=[V20CredFormat(attach_id="0", format_=V20CredFormat.Format.INDY)],
            requests_attach=[AttachDecorator.data_base64(indy_cred_req, ident="0")],
        )

        stored_cx_rec = V20CredExRecord(
            cred_ex_id="dummy-cxid",
            conn_id=conn_id,
            cred_proposal=cred_proposal.serialize(),
            cred_offer=cred_offer.serialize(),
            cred_request=cred_request.serialize(),
            initiator=V20CredExRecord.INITIATOR_SELF,
            role=V20CredExRecord.ROLE_ISSUER,
            state=V20CredExRecord.STATE_REQUEST_RECEIVED,
            thread_id=thread_id,
        )

        issuer = async_mock.MagicMock()
        indy_cred = {"indy": "credential"}
        issuer.create_credential = async_mock.CoroutineMock(
            return_value=(json.dumps(indy_cred), None)
        )
        self.context.injector.bind_instance(IndyIssuer, issuer)

        Ledger = async_mock.MagicMock()
        self.ledger = Ledger()
        self.ledger.get_schema = async_mock.CoroutineMock(return_value=SCHEMA)
        self.ledger.get_credential_definition = async_mock.CoroutineMock(
            return_value=CRED_DEF_NR
        )
        self.ledger.__aenter__ = async_mock.CoroutineMock(return_value=self.ledger)
        self.context.injector.clear_binding(BaseLedger)
        self.context.injector.bind_instance(BaseLedger, self.ledger)

        with async_mock.patch.object(
            V20CredExRecord, "save", autospec=True
        ) as mock_save:
            (ret_cx_rec, ret_cred_issue) = await self.manager.issue_credential(
                stored_cx_rec, comment=comment, retries=0
            )

            mock_save.assert_called_once()

            issuer.create_credential.assert_called_once_with(
                SCHEMA,
                indy_offer,
                indy_cred_req,
                attr_values,
                stored_cx_rec.cred_ex_id,
                None,
                None,
            )

            assert V20CredIssue.deserialize(ret_cx_rec.cred_issue).cred() == indy_cred
            assert ret_cred_issue.cred() == indy_cred
            assert ret_cx_rec.state == V20CredExRecord.STATE_ISSUED
            assert ret_cred_issue._thread_id == thread_id

    async def test_issue_credential_fills_rr(self):
        conn_id = "test_conn_id"
        comment = "comment"
        attr_values = {
            "legalName": "value",
            "jurisdictionId": "value",
            "incorporationDate": "value",
        }
        indy_offer = {
            "schema_id": SCHEMA_ID,
            "cred_def_id": CRED_DEF_ID,
            "nonce": "0",
            "...": "...",
        }
        indy_cred_req = {"schema_id": SCHEMA_ID, "cred_def_id": CRED_DEF_ID}
        thread_id = "thread-id"
        cred_rev_id = "1000"

        cred_preview = V20CredPreview(
            attributes=[
                V20CredAttrSpec(name=k, value=v) for (k, v) in attr_values.items()
            ]
        )
        cred_proposal = V20CredProposal(
            credential_preview=cred_preview,
            formats=[V20CredFormat(attach_id="0", format_=V20CredFormat.Format.INDY)],
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
            formats=[V20CredFormat(attach_id="0", format_=V20CredFormat.Format.INDY)],
            offers_attach=[AttachDecorator.data_base64(indy_offer, ident="0")],
        )
        cred_offer.assign_thread_id(thread_id)
        cred_request = V20CredRequest(
            formats=[V20CredFormat(attach_id="0", format_=V20CredFormat.Format.INDY)],
            requests_attach=[AttachDecorator.data_base64(indy_cred_req, ident="0")],
        )

        stored_cx_rec = V20CredExRecord(
            cred_ex_id="dummy-cxid",
            conn_id=conn_id,
            cred_proposal=cred_proposal.serialize(),
            cred_offer=cred_offer.serialize(),
            cred_request=cred_request.serialize(),
            initiator=V20CredExRecord.INITIATOR_SELF,
            role=V20CredExRecord.ROLE_ISSUER,
            state=V20CredExRecord.STATE_REQUEST_RECEIVED,
            thread_id=thread_id,
        )

        issuer = async_mock.MagicMock()
        indy_cred = {"indy": "credential"}
        issuer.create_credential = async_mock.CoroutineMock(
            return_value=(json.dumps(indy_cred), cred_rev_id)
        )
        self.context.injector.bind_instance(IndyIssuer, issuer)

        with async_mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as revoc, async_mock.patch.object(
            asyncio, "ensure_future", autospec=True
        ) as asyncio_mock, async_mock.patch.object(
            V20CredExRecord, "save", autospec=True
        ) as mock_save:
            revoc.return_value = async_mock.MagicMock(
                get_active_issuer_rev_reg_record=(
                    async_mock.CoroutineMock(
                        return_value=async_mock.MagicMock(  # active_rev_reg_rec
                            revoc_reg_id=REV_REG_ID,
                            get_registry=async_mock.CoroutineMock(
                                return_value=async_mock.MagicMock(  # rev_reg
                                    tails_local_path="dummy-path",
                                    max_creds=1000,
                                    get_or_fetch_local_tails_path=(
                                        async_mock.CoroutineMock()
                                    ),
                                )
                            ),
                            set_state=async_mock.CoroutineMock(),
                        )
                    )
                ),
                init_issuer_registry=async_mock.CoroutineMock(
                    return_value=async_mock.MagicMock(  # pending_rev_reg_rec
                        stage_pending_registry=async_mock.CoroutineMock()
                    )
                ),
            )
            (ret_cx_rec, ret_cred_issue) = await self.manager.issue_credential(
                stored_cx_rec, comment=comment, retries=0
            )

            mock_save.assert_called_once()

            issuer.create_credential.assert_called_once_with(
                SCHEMA,
                indy_offer,
                indy_cred_req,
                attr_values,
                stored_cx_rec.cred_ex_id,
                REV_REG_ID,
                "dummy-path",
            )

            assert V20CredIssue.deserialize(ret_cx_rec.cred_issue).cred() == indy_cred
            assert ret_cred_issue.cred() == indy_cred
            assert ret_cx_rec.state == V20CredExRecord.STATE_ISSUED
            assert ret_cred_issue._thread_id == thread_id

    async def test_issue_credential_request_bad_state(self):
        conn_id = "test_conn_id"
        attr_values = {
            "legalName": "value",
            "jurisdictionId": "value",
            "incorporationDate": "value",
        }
        thread_id = "thread-id"

        cred_preview = V20CredPreview(
            attributes=[
                V20CredAttrSpec(name=k, value=v) for (k, v) in attr_values.items()
            ]
        )
        cred_proposal = V20CredProposal(
            credential_preview=cred_preview,
            formats=[V20CredFormat(attach_id="0", format_=V20CredFormat.Format.INDY)],
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

        stored_cx_rec = V20CredExRecord(
            cred_ex_id="dummy-cxid",
            conn_id=conn_id,
            cred_proposal=cred_proposal.serialize(),
            initiator=V20CredExRecord.INITIATOR_SELF,
            role=V20CredExRecord.ROLE_ISSUER,
            state=V20CredExRecord.STATE_PROPOSAL_SENT,
            thread_id=thread_id,
        )

        with self.assertRaises(V20CredManagerError) as context:
            await self.manager.issue_credential(stored_cx_rec)
        assert " state " in str(context.exception)

    async def test_issue_credential_no_active_rr_no_retries(self):
        conn_id = "test_conn_id"
        comment = "comment"
        attr_values = {
            "legalName": "value",
            "jurisdictionId": "value",
            "incorporationDate": "value",
        }
        indy_offer = {
            "schema_id": SCHEMA_ID,
            "cred_def_id": CRED_DEF_ID,
            "nonce": "0",
            "...": "...",
        }
        indy_cred_req = {
            "schema_id": SCHEMA_ID,
            "cred_def_id": CRED_DEF_ID,
            "...": "...",
        }
        thread_id = "thread-id"

        cred_preview = V20CredPreview(
            attributes=[
                V20CredAttrSpec(name=k, value=v) for (k, v) in attr_values.items()
            ]
        )
        cred_proposal = V20CredProposal(
            credential_preview=cred_preview,
            formats=[V20CredFormat(attach_id="0", format_=V20CredFormat.Format.INDY)],
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
            formats=[V20CredFormat(attach_id="0", format_=V20CredFormat.Format.INDY)],
            offers_attach=[AttachDecorator.data_base64(indy_offer, ident="0")],
        )
        cred_offer.assign_thread_id(thread_id)
        cred_request = V20CredRequest(
            formats=[V20CredFormat(attach_id="0", format_=V20CredFormat.Format.INDY)],
            requests_attach=[AttachDecorator.data_base64(indy_cred_req, ident="0")],
        )

        stored_cx_rec = V20CredExRecord(
            cred_ex_id="dummy-cxid",
            conn_id=conn_id,
            cred_proposal=cred_proposal.serialize(),
            cred_offer=cred_offer.serialize(),
            cred_request=cred_request.serialize(),
            initiator=V20CredExRecord.INITIATOR_SELF,
            role=V20CredExRecord.ROLE_ISSUER,
            state=V20CredExRecord.STATE_REQUEST_RECEIVED,
            thread_id=thread_id,
        )

        issuer = async_mock.MagicMock()
        indy_cred = {"indy": "credential"}
        cred_rev_id = "1"
        issuer.create_credential = async_mock.CoroutineMock(
            return_value=(json.dumps(indy_cred), cred_rev_id)
        )
        self.context.injector.bind_instance(IndyIssuer, issuer)

        with async_mock.patch.object(
            test_module, "IssuerRevRegRecord", autospec=True
        ) as issuer_rr_rec, async_mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as revoc, async_mock.patch.object(
            V20CredExRecord, "save", autospec=True
        ) as mock_save:
            revoc.return_value.get_active_issuer_rev_reg_record = (
                async_mock.CoroutineMock(side_effect=StorageNotFoundError())
            )
            revoc.return_value.init_issuer_registry = async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(  # pending_rev_reg_rec
                    stage_pending_registry=async_mock.CoroutineMock()
                )
            )
            issuer_rr_rec.query_by_cred_def_id = async_mock.CoroutineMock(
                return_value=[]
            )
            with self.assertRaises(V20CredManagerError) as context:
                await self.manager.issue_credential(
                    stored_cx_rec, comment=comment, retries=0
                )
            assert "has no active revocation registry" in str(context.exception)

    async def test_issue_credential_no_active_rr_retry(self):
        conn_id = "test_conn_id"
        comment = "comment"
        attr_values = {
            "legalName": "value",
            "jurisdictionId": "value",
            "incorporationDate": "value",
        }
        indy_offer = {
            "schema_id": SCHEMA_ID,
            "cred_def_id": CRED_DEF_ID,
            "nonce": "0",
            "...": "...",
        }
        indy_cred_req = {
            "schema_id": SCHEMA_ID,
            "cred_def_id": CRED_DEF_ID,
            "...": "...",
        }
        thread_id = "thread-id"

        cred_preview = V20CredPreview(
            attributes=[
                V20CredAttrSpec(name=k, value=v) for (k, v) in attr_values.items()
            ]
        )
        cred_proposal = V20CredProposal(
            credential_preview=cred_preview,
            formats=[V20CredFormat(attach_id="0", format_=V20CredFormat.Format.INDY)],
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
            formats=[V20CredFormat(attach_id="0", format_=V20CredFormat.Format.INDY)],
            offers_attach=[AttachDecorator.data_base64(indy_offer, ident="0")],
        )
        cred_offer.assign_thread_id(thread_id)
        cred_request = V20CredRequest(
            formats=[V20CredFormat(attach_id="0", format_=V20CredFormat.Format.INDY)],
            requests_attach=[AttachDecorator.data_base64(indy_cred_req, ident="0")],
        )

        stored_cx_rec = V20CredExRecord(
            cred_ex_id="dummy-cxid",
            conn_id=conn_id,
            cred_proposal=cred_proposal.serialize(),
            cred_offer=cred_offer.serialize(),
            cred_request=cred_request.serialize(),
            initiator=V20CredExRecord.INITIATOR_SELF,
            role=V20CredExRecord.ROLE_ISSUER,
            state=V20CredExRecord.STATE_REQUEST_RECEIVED,
            thread_id=thread_id,
        )

        issuer = async_mock.MagicMock()
        indy_cred = {"indy": "credential"}
        cred_rev_id = "1"
        issuer.create_credential = async_mock.CoroutineMock(
            return_value=(json.dumps(indy_cred), cred_rev_id)
        )
        self.context.injector.bind_instance(IndyIssuer, issuer)

        with async_mock.patch.object(
            test_module, "IssuerRevRegRecord", autospec=True
        ) as issuer_rr_rec, async_mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as revoc, async_mock.patch.object(
            V20CredExRecord, "save", autospec=True
        ) as mock_save:
            revoc.return_value.get_active_issuer_rev_reg_record = (
                async_mock.CoroutineMock(side_effect=StorageNotFoundError())
            )
            issuer_rr_rec.query_by_cred_def_id = async_mock.CoroutineMock(
                side_effect=[
                    [],  # posted_rev_reg_recs
                    [async_mock.MagicMock(max_cred_num=1000)],  # old_rev_reg_recs
                ]
                * 2
            )
            revoc.return_value.init_issuer_registry = async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(  # pending_rev_reg_rec
                    stage_pending_registry=async_mock.CoroutineMock()
                )
            )
            with self.assertRaises(V20CredManagerError) as context:
                await self.manager.issue_credential(
                    stored_cx_rec, comment=comment, retries=1
                )
            assert "has no active revocation registry" in str(context.exception)

    async def test_issue_credential_rr_full(self):
        conn_id = "test_conn_id"
        comment = "comment"
        attr_values = {
            "legalName": "value",
            "jurisdictionId": "value",
            "incorporationDate": "value",
        }
        indy_offer = {
            "schema_id": SCHEMA_ID,
            "cred_def_id": CRED_DEF_ID,
            "nonce": "0",
            "...": "...",
        }
        indy_cred_req = {
            "schema_id": SCHEMA_ID,
            "cred_def_id": CRED_DEF_ID,
            "...": "...",
        }
        thread_id = "thread-id"

        cred_preview = V20CredPreview(
            attributes=[
                V20CredAttrSpec(name=k, value=v) for (k, v) in attr_values.items()
            ]
        )
        cred_proposal = V20CredProposal(
            credential_preview=cred_preview,
            formats=[V20CredFormat(attach_id="0", format_=V20CredFormat.Format.INDY)],
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
            formats=[V20CredFormat(attach_id="0", format_=V20CredFormat.Format.INDY)],
            offers_attach=[AttachDecorator.data_base64(indy_offer, ident="0")],
        )
        cred_offer.assign_thread_id(thread_id)
        cred_request = V20CredRequest(
            formats=[V20CredFormat(attach_id="0", format_=V20CredFormat.Format.INDY)],
            requests_attach=[AttachDecorator.data_base64(indy_cred_req, ident="0")],
        )

        stored_cx_rec = V20CredExRecord(
            cred_ex_id="dummy-cxid",
            conn_id=conn_id,
            cred_proposal=cred_proposal.serialize(),
            cred_offer=cred_offer.serialize(),
            cred_request=cred_request.serialize(),
            initiator=V20CredExRecord.INITIATOR_SELF,
            role=V20CredExRecord.ROLE_ISSUER,
            state=V20CredExRecord.STATE_REQUEST_RECEIVED,
            thread_id=thread_id,
        )

        issuer = async_mock.MagicMock()
        issuer.create_credential = async_mock.CoroutineMock(
            side_effect=test_module.IndyIssuerRevocationRegistryFullError("Nope")
        )
        self.context.injector.bind_instance(IndyIssuer, issuer)

        with async_mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as revoc:
            revoc.return_value.get_active_issuer_rev_reg_record = (
                async_mock.CoroutineMock(
                    return_value=async_mock.MagicMock(  # active_rev_reg_rec
                        revoc_reg_id=REV_REG_ID,
                        set_state=async_mock.CoroutineMock(),
                        get_registry=async_mock.CoroutineMock(
                            return_value=async_mock.MagicMock(  # rev_reg
                                tails_local_path="dummy-path",
                                get_or_fetch_local_tails_path=(
                                    async_mock.CoroutineMock()
                                ),
                            )
                        ),
                    )
                )
            )

            with self.assertRaises(test_module.IndyIssuerRevocationRegistryFullError):
                await self.manager.issue_credential(
                    stored_cx_rec, comment=comment, retries=1
                )

    async def test_receive_cred(self):
        conn_id = "test_conn_id"
        indy_cred = {"indy": "credential"}

        stored_cx_rec = V20CredExRecord(
            cred_ex_id="dummy-cxid",
            conn_id=conn_id,
            initiator=V20CredExRecord.INITIATOR_EXTERNAL,
            role=V20CredExRecord.ROLE_ISSUER,
        )

        cred_issue = V20CredIssue(
            formats=[V20CredFormat(attach_id="0", format_=V20CredFormat.Format.INDY)],
            credentials_attach=[AttachDecorator.data_base64(indy_cred, ident="0")],
        )

        with async_mock.patch.object(
            V20CredExRecord, "save", autospec=True
        ) as mock_save, async_mock.patch.object(
            V20CredExRecord,
            "retrieve_by_conn_and_thread",
            async_mock.CoroutineMock(),
        ) as mock_retrieve:
            mock_retrieve.return_value = stored_cx_rec
            ret_cx_rec = await self.manager.receive_credential(cred_issue, conn_id)

            mock_retrieve.assert_called_once_with(
                self.session, conn_id, cred_issue._thread_id
            )
            mock_save.assert_called_once()

            assert V20CredIssue.deserialize(ret_cx_rec.cred_issue).cred() == indy_cred
            assert ret_cx_rec.state == V20CredExRecord.STATE_CREDENTIAL_RECEIVED

    async def test_store_credential(self):
        conn_id = "test_conn_id"
        attr_values = {
            "legalName": ["value", None],
            "jurisdictionId": ["value", None],
            "incorporationDate": ["value", None],
            "pic": ["cG90YXRv", "image/jpeg"],
        }
        indy_cred = {"cred_def_id": CRED_DEF_ID, "rev_reg_id": REV_REG_ID, "...": "..."}
        cred_req_meta = {"req": "meta"}
        thread_id = "thread-id"
        indy_offer = {
            "schema_id": SCHEMA_ID,
            "cred_def_id": CRED_DEF_ID,
            "nonce": "0",
            "...": "...",
        }
        indy_cred_req = {
            "schema_id": SCHEMA_ID,
            "cred_def_id": CRED_DEF_ID,
            "...": "...",
        }

        cred_preview = V20CredPreview(
            attributes=[
                V20CredAttrSpec(name=k, value=v[0], mime_type=v[1])
                for (k, v) in attr_values.items()
            ]
        )
        cred_proposal = V20CredProposal(
            credential_preview=cred_preview,
            formats=[V20CredFormat(attach_id="0", format_=V20CredFormat.Format.INDY)],
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
            formats=[V20CredFormat(attach_id="0", format_=V20CredFormat.Format.INDY)],
            offers_attach=[AttachDecorator.data_base64(indy_offer, ident="0")],
        )
        cred_offer.assign_thread_id(thread_id)
        cred_request = V20CredRequest(
            formats=[V20CredFormat(attach_id="0", format_=V20CredFormat.Format.INDY)],
            requests_attach=[AttachDecorator.data_base64(indy_cred_req, ident="0")],
        )
        cred_issue = V20CredIssue(
            formats=[V20CredFormat(attach_id="0", format_=V20CredFormat.Format.INDY)],
            credentials_attach=[AttachDecorator.data_base64(indy_cred, ident="0")],
        )

        stored_cx_rec = V20CredExRecord(
            cred_ex_id="dummy-cxid",
            conn_id=conn_id,
            cred_proposal=cred_proposal.serialize(),
            cred_offer=cred_offer.serialize(),
            cred_request=cred_request.serialize(),
            cred_issue=cred_issue.serialize(),
            initiator=V20CredExRecord.INITIATOR_EXTERNAL,
            role=V20CredExRecord.ROLE_ISSUER,
            state=V20CredExRecord.STATE_CREDENTIAL_RECEIVED,
            thread_id=thread_id,
            auto_remove=True,
        )

        cred_id = "cred-id"
        holder = async_mock.MagicMock()
        holder.store_credential = async_mock.CoroutineMock(return_value=cred_id)
        stored_cred = {"stored": "cred"}
        holder.get_credential = async_mock.CoroutineMock(
            return_value=json.dumps(stored_cred)
        )
        self.context.injector.bind_instance(IndyHolder, holder)

        with async_mock.patch.object(
            test_module, "RevocationRegistry", autospec=True
        ) as mock_rev_reg, async_mock.patch.object(
            V20CredExRecord, "save", autospec=True
        ) as mock_save, async_mock.patch.object(
            V20CredExRecord, "delete_record", autospec=True
        ) as mock_delete:
            mock_rev_reg.from_definition = async_mock.MagicMock(
                return_value=async_mock.MagicMock(
                    get_or_fetch_local_tails_path=async_mock.CoroutineMock()
                )
            )
            with self.assertRaises(V20CredManagerError) as context:
                await self.manager.store_credential(stored_cx_rec, cred_id=cred_id)
            assert "No credential exchange " in str(context.exception)

        with async_mock.patch.object(
            test_module, "RevocationRegistry", autospec=True
        ) as mock_rev_reg, async_mock.patch.object(
            V20CredExRecord, "save", autospec=True
        ) as mock_save, async_mock.patch.object(
            test_module.V20CredManager, "delete_cred_ex_record", autospec=True
        ) as mock_delete, async_mock.patch.object(
            test_module.V20CredManager, "get_detail_record", autospec=True
        ) as mock_get_detail_record:
            mock_rev_reg.from_definition = async_mock.MagicMock(
                return_value=async_mock.MagicMock(
                    get_or_fetch_local_tails_path=async_mock.CoroutineMock()
                )
            )
            mock_get_detail_record.return_value = async_mock.MagicMock(
                cred_request_metadata=cred_req_meta,
                save=async_mock.CoroutineMock(),
            )

            self.ledger.get_credential_definition.reset_mock()
            ret_cx_rec, ret_cred_ack = await self.manager.store_credential(
                stored_cx_rec, cred_id=cred_id
            )

            mock_save.assert_called_once()

            self.ledger.get_credential_definition.assert_called_once_with(CRED_DEF_ID)

            holder.store_credential.assert_called_once_with(
                CRED_DEF,
                indy_cred,
                cred_req_meta,
                {"pic": "image/jpeg"},
                credential_id=cred_id,
                rev_reg_def=REV_REG_DEF,
            )

            assert V20CredIssue.deserialize(ret_cx_rec.cred_issue).cred() == indy_cred
            assert ret_cx_rec.state == V20CredExRecord.STATE_DONE
            assert ret_cred_ack._thread_id == thread_id

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

    async def test_store_credential_holder_store_indy_error(self):
        conn_id = "test_conn_id"
        indy_cred = {"cred_def_id": CRED_DEF_ID, "...": "..."}
        cred_req_meta = {"req": "meta"}
        thread_id = "thread-id"
        attr_values = {
            "legalName": ["value", None],
            "jurisdictionId": ["value", None],
            "incorporationDate": ["value", None],
            "pic": ["cG90YXRv", "image/jpeg"],
        }
        indy_offer = {
            "schema_id": SCHEMA_ID,
            "cred_def_id": CRED_DEF_ID,
            "nonce": "0",
            "...": "...",
        }
        indy_cred_req = {
            "schema_id": SCHEMA_ID,
            "cred_def_id": CRED_DEF_ID,
            "...": "...",
        }

        cred_preview = V20CredPreview(
            attributes=[
                V20CredAttrSpec(name=k, value=v[0], mime_type=v[1])
                for (k, v) in attr_values.items()
            ]
        )
        cred_proposal = V20CredProposal(
            credential_preview=cred_preview,
            formats=[V20CredFormat(attach_id="0", format_=V20CredFormat.Format.INDY)],
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
            formats=[V20CredFormat(attach_id="0", format_=V20CredFormat.Format.INDY)],
            offers_attach=[AttachDecorator.data_base64(indy_offer, ident="0")],
        )
        cred_offer.assign_thread_id(thread_id)
        cred_request = V20CredRequest(
            formats=[V20CredFormat(attach_id="0", format_=V20CredFormat.Format.INDY)],
            requests_attach=[AttachDecorator.data_base64(indy_cred_req, ident="0")],
        )
        cred_issue = V20CredIssue(
            formats=[V20CredFormat(attach_id="0", format_=V20CredFormat.Format.INDY)],
            credentials_attach=[AttachDecorator.data_base64(indy_cred, ident="0")],
        )

        stored_cx_rec = V20CredExRecord(
            cred_ex_id="dummy-cxid",
            conn_id=conn_id,
            cred_proposal=cred_proposal.serialize(),
            cred_offer=cred_offer.serialize(),
            cred_request=cred_request.serialize(),
            cred_issue=cred_issue.serialize(),
            initiator=V20CredExRecord.INITIATOR_EXTERNAL,
            role=V20CredExRecord.ROLE_HOLDER,
            state=V20CredExRecord.STATE_CREDENTIAL_RECEIVED,
            thread_id=thread_id,
            auto_remove=True,
        )

        cred_def = async_mock.MagicMock()
        self.ledger.get_credential_definition = async_mock.CoroutineMock(
            return_value=cred_def
        )

        cred_id = "cred-id"
        holder = async_mock.MagicMock()
        holder.store_credential = async_mock.CoroutineMock(
            side_effect=test_module.IndyHolderError("Problem", {"message": "Nope"})
        )
        self.context.injector.bind_instance(IndyHolder, holder)

        with async_mock.patch.object(
            test_module.V20CredManager, "get_detail_record", autospec=True
        ) as mock_get_detail_record:
            mock_get_detail_record.return_value = async_mock.MagicMock(
                cred_request_metadata=cred_req_meta,
                save=async_mock.CoroutineMock(),
            )
            with self.assertRaises(test_module.IndyHolderError) as context:
                await self.manager.store_credential(
                    cred_ex_record=stored_cx_rec, cred_id=cred_id
                )
            assert "Nope" in str(context.exception)

    async def test_credential_ack(self):
        conn_id = "conn-id"
        stored_cx_rec = V20CredExRecord(
            cred_ex_id="dummy-cxid",
            conn_id=conn_id,
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
                conn_id,
            )

            mock_retrieve.assert_called_once_with(self.session, conn_id, ack._thread_id)
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
                        retrieve_by_cred_ex_id=async_mock.CoroutineMock(
                            return_value=stored_indy
                        )
                    )
                ),
                async_mock.MagicMock(
                    detail=async_mock.MagicMock(
                        retrieve_by_cred_ex_id=async_mock.CoroutineMock(
                            side_effect=StorageNotFoundError()
                        )
                    )
                ),
            ]
            await self.manager.delete_cred_ex_record("dummy")

    async def test_retrieve_records(self):
        self.cache = InMemoryCache()
        self.session.context.injector.bind_instance(BaseCache, self.cache)

        for index in range(2):
            cx_rec = V20CredExRecord(
                conn_id=str(index),
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
                assert ret_ex.conn_id == str(index)
                assert ret_ex.thread_id == str(1000 + index)
