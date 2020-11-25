import asyncio
import json

from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock
from copy import deepcopy
from time import time

from .....config.injection_context import InjectionContext
from .....cache.base import BaseCache
from .....cache.basic import BasicCache
from .....indy.holder import IndyHolder
from .....indy.issuer import IndyIssuer
from .....messaging.credential_definitions.util import CRED_DEF_SENT_RECORD_TYPE
from .....messaging.request_context import RequestContext
from .....ledger.base import BaseLedger
from .....storage.base import BaseStorage, StorageRecord
from .....storage.basic import BasicStorage
from .....storage.error import StorageNotFoundError

from ..manager import CredentialManager, CredentialManagerError
from ..messages.credential_ack import CredentialAck
from ..messages.credential_issue import CredentialIssue
from ..messages.credential_offer import CredentialOffer
from ..messages.credential_proposal import CredentialProposal
from ..messages.credential_request import CredentialRequest
from ..messages.inner.credential_preview import CredentialPreview, CredAttrSpec
from ..models.credential_exchange import V10CredentialExchange

from .. import manager as test_module


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


class TestCredentialManager(AsyncTestCase):
    async def setUp(self):
        self.context = RequestContext(
            base_context=InjectionContext(enforce_typing=False)
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

        self.manager = CredentialManager(self.context)

    async def test_record_eq(self):
        same = [
            V10CredentialExchange(
                credential_exchange_id="dummy-0",
                thread_id="thread-0",
                credential_definition_id=CRED_DEF_ID,
                role=V10CredentialExchange.ROLE_ISSUER,
            )
        ] * 2
        diff = [
            V10CredentialExchange(
                credential_exchange_id="dummy-1",
                credential_definition_id=CRED_DEF_ID,
                role=V10CredentialExchange.ROLE_ISSUER,
            ),
            V10CredentialExchange(
                credential_exchange_id="dummy-0",
                thread_id="thread-1",
                credential_definition_id=CRED_DEF_ID,
                role=V10CredentialExchange.ROLE_ISSUER,
            ),
            V10CredentialExchange(
                credential_exchange_id="dummy-1",
                thread_id="thread-0",
                credential_definition_id=f"{CRED_DEF_ID}_distinct_tag",
                role=V10CredentialExchange.ROLE_ISSUER,
            ),
        ]

        for i in range(len(same) - 1):
            for j in range(i, len(same)):
                assert same[i] == same[j]

        for i in range(len(diff) - 1):
            for j in range(i, len(diff)):
                assert diff[i] == diff[j] if i == j else diff[i] != diff[j]

    async def test_prepare_send(self):
        connection_id = "test_conn_id"
        preview = CredentialPreview(
            attributes=(
                CredAttrSpec(name="legalName", value="value"),
                CredAttrSpec(name="jurisdictionId", value="value"),
                CredAttrSpec(name="incorporationDate", value="value"),
            )
        )
        proposal = CredentialProposal(
            credential_proposal=preview, cred_def_id=CRED_DEF_ID, schema_id=SCHEMA_ID
        )
        with async_mock.patch.object(
            self.manager, "create_offer", autospec=True
        ) as create_offer:
            create_offer.return_value = (async_mock.MagicMock(), async_mock.MagicMock())
            ret_exchange, ret_cred_offer = await self.manager.prepare_send(
                connection_id, proposal
            )
            create_offer.assert_called_once()
            assert ret_exchange is create_offer.return_value[0]
            arg_exchange = create_offer.call_args[1]["cred_ex_record"]
            assert arg_exchange.auto_issue
            assert arg_exchange.connection_id == connection_id
            assert arg_exchange.schema_id == None
            assert arg_exchange.credential_definition_id == None
            assert arg_exchange.role == V10CredentialExchange.ROLE_ISSUER
            assert arg_exchange.credential_proposal_dict == proposal.serialize()

    async def test_create_proposal(self):
        connection_id = "test_conn_id"
        comment = "comment"
        preview = CredentialPreview(
            attributes=(
                CredAttrSpec(name="legalName", value="value"),
                CredAttrSpec(name="jurisdictionId", value="value"),
                CredAttrSpec(name="incorporationDate", value="value"),
            )
        )

        self.ledger.credential_definition_id2schema_id = async_mock.CoroutineMock(
            return_value=SCHEMA_ID
        )

        with async_mock.patch.object(
            V10CredentialExchange, "save", autospec=True
        ) as save_ex:
            exchange: V10CredentialExchange = await self.manager.create_proposal(
                connection_id,
                auto_offer=True,
                comment=comment,
                credential_preview=preview,
                cred_def_id=CRED_DEF_ID,
            )
            save_ex.assert_called_once()

            await self.manager.create_proposal(
                connection_id,
                auto_offer=True,
                comment=comment,
                credential_preview=preview,
                cred_def_id=None,
            )  # OK to leave underspecified until offer

        proposal = CredentialProposal.deserialize(exchange.credential_proposal_dict)

        assert exchange.auto_offer
        assert exchange.connection_id == connection_id
        assert not exchange.credential_definition_id  # leave underspecified until offer
        assert not exchange.schema_id  # leave underspecified until offer
        assert exchange.thread_id == proposal._thread_id
        assert exchange.role == exchange.ROLE_HOLDER
        assert exchange.state == V10CredentialExchange.STATE_PROPOSAL_SENT

    async def test_create_proposal_no_preview(self):
        connection_id = "test_conn_id"
        comment = "comment"

        self.ledger.credential_definition_id2schema_id = async_mock.CoroutineMock(
            return_value=SCHEMA_ID
        )

        with async_mock.patch.object(
            V10CredentialExchange, "save", autospec=True
        ) as save_ex:
            exchange: V10CredentialExchange = await self.manager.create_proposal(
                connection_id,
                auto_offer=True,
                comment=comment,
                credential_preview=None,
                cred_def_id=CRED_DEF_ID,
            )
            save_ex.assert_called_once()

        proposal = CredentialProposal.deserialize(exchange.credential_proposal_dict)

        assert exchange.auto_offer
        assert exchange.connection_id == connection_id
        assert not exchange.credential_definition_id  # leave underspecified until offer
        assert not exchange.schema_id  # leave underspecified until offer
        assert exchange.thread_id == proposal._thread_id
        assert exchange.role == exchange.ROLE_HOLDER
        assert exchange.state == V10CredentialExchange.STATE_PROPOSAL_SENT

    async def test_receive_proposal(self):
        connection_id = "test_conn_id"
        comment = "comment"

        preview = CredentialPreview(
            attributes=(
                CredAttrSpec(name="legalName", value="value"),
                CredAttrSpec(name="jurisdictionId", value="value"),
                CredAttrSpec(name="incorporationDate", value="value"),
            )
        )
        self.context.connection_record = async_mock.MagicMock()
        self.context.connection_record.connection_id = connection_id

        with async_mock.patch.object(
            V10CredentialExchange, "save", autospec=True
        ) as save_ex:
            proposal = CredentialProposal(
                credential_proposal=preview, cred_def_id=CRED_DEF_ID, schema_id=None
            )
            self.context.message = proposal

            exchange = await self.manager.receive_proposal()
            save_ex.assert_called_once()

            assert exchange.connection_id == connection_id
            assert exchange.credential_definition_id == None
            assert exchange.role == V10CredentialExchange.ROLE_ISSUER
            assert exchange.state == V10CredentialExchange.STATE_PROPOSAL_RECEIVED
            assert exchange.schema_id == None
            assert exchange.thread_id == proposal._thread_id

            ret_proposal: CredentialProposal = CredentialProposal.deserialize(
                exchange.credential_proposal_dict
            )
            attrs = ret_proposal.credential_proposal.attributes
            assert attrs == preview.attributes

            self.context.message = CredentialProposal(
                credential_proposal=preview, cred_def_id=None, schema_id=None
            )
            await self.manager.receive_proposal()  # OK to leave open until offer

    async def test_create_free_offer(self):
        connection_id = "test_conn_id"
        comment = "comment"
        schema_id_parts = SCHEMA_ID.split(":")

        preview = CredentialPreview(
            attributes=(
                CredAttrSpec(name="legalName", value="value"),
                CredAttrSpec(name="jurisdictionId", value="value"),
                CredAttrSpec(name="incorporationDate", value="value"),
            )
        )
        proposal = CredentialProposal(
            credential_proposal=preview, cred_def_id=CRED_DEF_ID, schema_id=None
        )

        exchange = V10CredentialExchange(
            credential_exchange_id="dummy-cxid",
            credential_definition_id=CRED_DEF_ID,
            role=V10CredentialExchange.ROLE_ISSUER,
            credential_proposal_dict=proposal.serialize(),
        )

        with async_mock.patch.object(
            V10CredentialExchange, "save", autospec=True
        ) as save_ex:

            self.cache = BasicCache()
            self.context.injector.bind_instance(BaseCache, self.cache)

            cred_offer = {"cred_def_id": CRED_DEF_ID, "schema_id": SCHEMA_ID}

            issuer = async_mock.MagicMock(IndyIssuer, autospec=True)
            issuer.create_credential_offer = async_mock.CoroutineMock(
                return_value=json.dumps(cred_offer)
            )
            self.context.injector.bind_instance(IndyIssuer, issuer)

            self.storage = BasicStorage()
            self.context.injector.bind_instance(BaseStorage, self.storage)
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
            storage: BaseStorage =  self.context.inject(BaseStorage)
            await storage.add_record(cred_def_record)

            (ret_exchange, ret_offer) = await self.manager.create_offer(
                cred_ex_record=exchange, comment=comment
            )
            assert ret_exchange is exchange
            save_ex.assert_called_once()

            issuer.create_credential_offer.assert_called_once_with(CRED_DEF_ID)

            assert exchange.credential_exchange_id == ret_exchange._id  # cover property
            assert exchange.thread_id == ret_offer._thread_id
            assert exchange.credential_definition_id == CRED_DEF_ID
            assert exchange.role == V10CredentialExchange.ROLE_ISSUER
            assert exchange.schema_id == SCHEMA_ID
            assert exchange.state == V10CredentialExchange.STATE_OFFER_SENT
            assert exchange.credential_offer == cred_offer

            (ret_exchange, ret_offer) = await self.manager.create_offer(
                cred_ex_record=exchange, comment=comment
            )  # once more to cover case where offer is available in cache

    async def test_create_free_offer_attr_mismatch(self):
        connection_id = "test_conn_id"
        comment = "comment"
        schema_id_parts = SCHEMA_ID.split(":")

        preview = CredentialPreview(
            attributes=(
                CredAttrSpec(name="legal name", value="value"),
                CredAttrSpec(name="jurisdiction id", value="value"),
                CredAttrSpec(name="incorporation date", value="value"),
            )
        )
        proposal = CredentialProposal(
            credential_proposal=preview, cred_def_id=CRED_DEF_ID, schema_id=None
        )

        exchange = V10CredentialExchange(
            credential_exchange_id="dummy-cxid",
            credential_definition_id=CRED_DEF_ID,
            role=V10CredentialExchange.ROLE_ISSUER,
            credential_proposal_dict=proposal.serialize(),
        )

        with async_mock.patch.object(
            V10CredentialExchange, "save", autospec=True
        ) as save_ex:
            self.cache = BasicCache()
            self.context.injector.bind_instance(BaseCache, self.cache)

            cred_offer = {"cred_def_id": CRED_DEF_ID, "schema_id": SCHEMA_ID}

            issuer = async_mock.MagicMock(IndyIssuer, autospec=True)
            issuer.create_credential_offer = async_mock.CoroutineMock(
                return_value=json.dumps(cred_offer)
            )
            self.context.injector.bind_instance(IndyIssuer, issuer)

            self.storage = BasicStorage()
            self.context.injector.bind_instance(BaseStorage, self.storage)
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
            storage: BaseStorage =  self.context.inject(BaseStorage)
            await storage.add_record(cred_def_record)

            with self.assertRaises(CredentialManagerError):
                await self.manager.create_offer(
                    cred_ex_record=exchange, comment=comment
                )

    async def test_create_bound_offer(self):
        TEST_DID = "LjgpST2rjsoxYegQDRm7EL"
        schema_id_parts = SCHEMA_ID.split(":")
        connection_id = "test_conn_id"
        comment = "comment"

        preview = CredentialPreview(
            attributes=(
                CredAttrSpec(name="legalName", value="value"),
                CredAttrSpec(name="jurisdictionId", value="value"),
                CredAttrSpec(name="incorporationDate", value="value"),
            )
        )
        proposal = CredentialProposal(credential_proposal=preview)
        exchange = V10CredentialExchange(
            credential_exchange_id="dummy-cxid",
            credential_proposal_dict=proposal.serialize(),
            role=V10CredentialExchange.ROLE_ISSUER,
        )

        with async_mock.patch.object(
            V10CredentialExchange, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            V10CredentialExchange, "get_cached_key", autospec=True
        ) as get_cached_key, async_mock.patch.object(
            V10CredentialExchange, "set_cached_key", autospec=True
        ) as set_cached_key:
            get_cached_key.return_value = None
            cred_offer = {"cred_def_id": CRED_DEF_ID, "schema_id": SCHEMA_ID}
            issuer = async_mock.MagicMock(IndyIssuer, autospec=True)
            issuer.create_credential_offer = async_mock.CoroutineMock(
                return_value=json.dumps(cred_offer)
            )
            self.context.injector.bind_instance(IndyIssuer, issuer)

            self.storage = BasicStorage()
            self.context.injector.bind_instance(BaseStorage, self.storage)
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
            storage: BaseStorage =  self.context.inject(BaseStorage)
            await storage.add_record(cred_def_record)

            (ret_exchange, ret_offer) = await self.manager.create_offer(
                cred_ex_record=exchange, comment=comment
            )
            assert ret_exchange is exchange
            save_ex.assert_called_once()

            issuer.create_credential_offer.assert_called_once_with(CRED_DEF_ID)

            assert exchange.thread_id == ret_offer._thread_id
            assert exchange.schema_id == SCHEMA_ID
            assert exchange.credential_definition_id == CRED_DEF_ID
            assert exchange.role == V10CredentialExchange.ROLE_ISSUER
            assert exchange.state == V10CredentialExchange.STATE_OFFER_SENT
            assert exchange.credential_offer == cred_offer

            # additionally check that credential preview was passed through
            assert ret_offer.credential_preview.attributes == preview.attributes

    async def test_create_bound_offer_no_cred_def(self):
        TEST_DID = "LjgpST2rjsoxYegQDRm7EL"
        schema_id_parts = SCHEMA_ID.split(":")
        connection_id = "test_conn_id"
        comment = "comment"

        preview = CredentialPreview(
            attributes=(
                CredAttrSpec(name="legalName", value="value"),
                CredAttrSpec(name="jurisdictionId", value="value"),
                CredAttrSpec(name="incorporationDate", value="value"),
            )
        )
        proposal = CredentialProposal(credential_proposal=preview)
        exchange = V10CredentialExchange(
            credential_exchange_id="dummy-cxid",
            credential_proposal_dict=proposal.serialize(),
            role=V10CredentialExchange.ROLE_ISSUER,
        )

        with async_mock.patch.object(
            V10CredentialExchange, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            V10CredentialExchange, "get_cached_key", autospec=True
        ) as get_cached_key, async_mock.patch.object(
            V10CredentialExchange, "set_cached_key", autospec=True
        ) as set_cached_key:
            get_cached_key.return_value = None
            cred_offer = {"cred_def_id": CRED_DEF_ID, "schema_id": SCHEMA_ID}
            issuer = async_mock.MagicMock()
            issuer.create_credential_offer = async_mock.CoroutineMock(
                return_value=cred_offer
            )
            self.context.injector.bind_instance(IndyIssuer, issuer)

            self.storage = BasicStorage()
            self.context.injector.bind_instance(BaseStorage, self.storage)

            with self.assertRaises(CredentialManagerError):
                await self.manager.create_offer(
                    cred_ex_record=exchange, comment=comment
                )

    async def test_receive_offer_proposed(self):
        connection_id = "test_conn_id"
        indy_offer = {"schema_id": SCHEMA_ID, "cred_def_id": CRED_DEF_ID}
        thread_id = "thread-id"

        preview = CredentialPreview(
            attributes=(
                CredAttrSpec(name="legalName", value="value"),
                CredAttrSpec(name="jurisdictionId", value="value"),
                CredAttrSpec(name="incorporationDate", value="value"),
            )
        )
        proposal = CredentialProposal(credential_proposal=preview)

        offer = CredentialOffer(
            credential_preview=preview,
            offers_attach=[CredentialOffer.wrap_indy_offer(indy_offer)],
        )
        offer.assign_thread_id(thread_id)

        self.context.message = offer
        self.context.connection_record = async_mock.MagicMock()
        self.context.connection_record.connection_id = connection_id

        stored_exchange = V10CredentialExchange(
            credential_exchange_id="dummy-cxid",
            connection_id=connection_id,
            credential_definition_id=CRED_DEF_ID,
            credential_proposal_dict=proposal.serialize(),
            initiator=V10CredentialExchange.INITIATOR_EXTERNAL,
            role=V10CredentialExchange.ROLE_HOLDER,
            schema_id=SCHEMA_ID,
            thread_id=thread_id,
        )

        with async_mock.patch.object(
            V10CredentialExchange, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            V10CredentialExchange,
            "retrieve_by_connection_and_thread",
            async_mock.CoroutineMock(return_value=stored_exchange),
        ) as retrieve_ex:
            exchange = await self.manager.receive_offer()

            assert exchange.connection_id == connection_id
            assert exchange.credential_definition_id == CRED_DEF_ID
            assert exchange.schema_id == SCHEMA_ID
            assert exchange.thread_id == offer._thread_id
            assert exchange.role == V10CredentialExchange.ROLE_HOLDER
            assert exchange.state == V10CredentialExchange.STATE_OFFER_RECEIVED
            assert exchange.credential_offer == indy_offer

            proposal = CredentialProposal.deserialize(exchange.credential_proposal_dict)
            assert proposal.credential_proposal.attributes == preview.attributes

    async def test_receive_free_offer(self):
        connection_id = "test_conn_id"
        indy_offer = {"schema_id": SCHEMA_ID, "cred_def_id": CRED_DEF_ID}
        preview = CredentialPreview(
            attributes=(
                CredAttrSpec(name="legalName", value="value"),
                CredAttrSpec(name="jurisdictionId", value="value"),
                CredAttrSpec(name="incorporationDate", value="value"),
            )
        )

        offer = CredentialOffer(
            credential_preview=preview,
            offers_attach=[CredentialOffer.wrap_indy_offer(indy_offer)],
        )
        self.context.message = offer
        self.context.connection_record = async_mock.MagicMock()
        self.context.connection_record.connection_id = connection_id

        with async_mock.patch.object(
            V10CredentialExchange, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            V10CredentialExchange,
            "retrieve_by_connection_and_thread",
            async_mock.CoroutineMock(side_effect=StorageNotFoundError),
        ) as retrieve_ex:
            exchange = await self.manager.receive_offer()

            assert exchange.connection_id == connection_id
            assert exchange.credential_definition_id == CRED_DEF_ID
            assert exchange.schema_id == SCHEMA_ID
            assert exchange.thread_id == offer._thread_id
            assert exchange.role == V10CredentialExchange.ROLE_HOLDER
            assert exchange.state == V10CredentialExchange.STATE_OFFER_RECEIVED
            assert exchange.credential_offer == indy_offer
            assert exchange.credential_proposal_dict

    async def test_create_request(self):
        connection_id = "test_conn_id"
        nonce = "0"
        indy_offer = {
            "schema_id": SCHEMA_ID,
            "cred_def_id": CRED_DEF_ID,
            "nonce": nonce,
        }
        indy_cred_req = {"schema_id": SCHEMA_ID, "cred_def_id": CRED_DEF_ID}
        thread_id = "thread-id"
        holder_did = "did"

        stored_exchange = V10CredentialExchange(
            credential_exchange_id="dummy-cxid",
            connection_id=connection_id,
            credential_definition_id=CRED_DEF_ID,
            credential_offer=indy_offer,
            initiator=V10CredentialExchange.INITIATOR_SELF,
            role=V10CredentialExchange.ROLE_HOLDER,
            state=V10CredentialExchange.STATE_OFFER_RECEIVED,
            schema_id=SCHEMA_ID,
            thread_id=thread_id,
        )

        self.cache = BasicCache()
        self.context.injector.bind_instance(BaseCache, self.cache)

        with async_mock.patch.object(
            V10CredentialExchange, "save", autospec=True
        ) as save_ex:
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

            ret_exchange, ret_request = await self.manager.create_request(
                stored_exchange, holder_did
            )

            holder.create_credential_request.assert_called_once_with(
                indy_offer, cred_def, holder_did
            )

            assert ret_request.indy_cred_req() == indy_cred_req
            assert ret_request._thread_id == thread_id

            assert ret_exchange.state == V10CredentialExchange.STATE_REQUEST_SENT

            # cover case with request in cache
            stored_exchange.credential_request = None
            stored_exchange.state = V10CredentialExchange.STATE_OFFER_RECEIVED
            await self.manager.create_request(stored_exchange, holder_did)

            # cover case with existing cred req
            stored_exchange.state = V10CredentialExchange.STATE_OFFER_RECEIVED
            stored_exchange.credential_request = indy_cred_req
            (
                ret_existing_exchange,
                ret_existing_request,
            ) = await self.manager.create_request(stored_exchange, holder_did)
            assert ret_existing_exchange == ret_exchange
            assert ret_existing_request._thread_id == thread_id

    async def test_create_request_no_cache(self):
        connection_id = "test_conn_id"
        nonce = "0"
        indy_offer = {
            "schema_id": SCHEMA_ID,
            "cred_def_id": CRED_DEF_ID,
            "nonce": nonce,
        }
        indy_cred_req = {"schema_id": SCHEMA_ID, "cred_def_id": CRED_DEF_ID}
        thread_id = "thread-id"
        holder_did = "did"

        stored_exchange = V10CredentialExchange(
            credential_exchange_id="dummy-cxid",
            connection_id=connection_id,
            credential_definition_id=CRED_DEF_ID,
            credential_offer=indy_offer,
            initiator=V10CredentialExchange.INITIATOR_SELF,
            role=V10CredentialExchange.ROLE_HOLDER,
            state=V10CredentialExchange.STATE_OFFER_RECEIVED,
            schema_id=SCHEMA_ID,
            thread_id=thread_id,
        )

        with async_mock.patch.object(
            V10CredentialExchange, "save", autospec=True
        ) as save_ex:
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

            ret_exchange, ret_request = await self.manager.create_request(
                stored_exchange, holder_did
            )

            holder.create_credential_request.assert_called_once_with(
                indy_offer, cred_def, holder_did
            )

            assert ret_request.indy_cred_req() == indy_cred_req
            assert ret_request._thread_id == thread_id

            assert ret_exchange.state == V10CredentialExchange.STATE_REQUEST_SENT

    async def test_create_request_bad_state(self):
        connection_id = "test_conn_id"
        indy_offer = {"schema_id": SCHEMA_ID, "cred_def_id": CRED_DEF_ID}
        indy_cred_req = {"schema_id": SCHEMA_ID, "cred_def_id": CRED_DEF_ID}
        thread_id = "thread-id"
        holder_did = "did"

        stored_exchange = V10CredentialExchange(
            credential_exchange_id="dummy-cxid",
            connection_id=connection_id,
            credential_definition_id=CRED_DEF_ID,
            credential_offer=indy_offer,
            initiator=V10CredentialExchange.INITIATOR_SELF,
            role=V10CredentialExchange.ROLE_HOLDER,
            state=V10CredentialExchange.STATE_PROPOSAL_SENT,
            schema_id=SCHEMA_ID,
            thread_id=thread_id,
        )

        with self.assertRaises(CredentialManagerError):
            await self.manager.create_request(stored_exchange, holder_did)

    async def test_create_request_no_nonce(self):
        connection_id = "test_conn_id"
        indy_offer = {"schema_id": SCHEMA_ID, "cred_def_id": CRED_DEF_ID}
        indy_cred_req = {"schema_id": SCHEMA_ID, "cred_def_id": CRED_DEF_ID}
        thread_id = "thread-id"
        holder_did = "did"

        stored_exchange = V10CredentialExchange(
            credential_exchange_id="dummy-cxid",
            connection_id=connection_id,
            credential_definition_id=CRED_DEF_ID,
            credential_offer=indy_offer,
            initiator=V10CredentialExchange.INITIATOR_SELF,
            role=V10CredentialExchange.ROLE_HOLDER,
            state=V10CredentialExchange.STATE_OFFER_RECEIVED,
            schema_id=SCHEMA_ID,
            thread_id=thread_id,
        )

        with self.assertRaises(CredentialManagerError):
            await self.manager.create_request(stored_exchange, holder_did)

    async def test_receive_request(self):
        connection_id = "test_conn_id"
        indy_cred_req = {"schema_id": SCHEMA_ID, "cred_def_id": CRED_DEF_ID}

        stored_exchange = V10CredentialExchange(
            credential_exchange_id="dummy-cxid",
            connection_id=connection_id,
            initiator=V10CredentialExchange.INITIATOR_EXTERNAL,
            role=V10CredentialExchange.ROLE_ISSUER,
        )

        request = CredentialRequest(
            requests_attach=[CredentialRequest.wrap_indy_cred_req(indy_cred_req)]
        )
        self.context.message = request
        self.context.connection_record = async_mock.MagicMock()
        self.context.connection_record.connection_id = connection_id

        with async_mock.patch.object(
            V10CredentialExchange, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            V10CredentialExchange,
            "retrieve_by_connection_and_thread",
            async_mock.CoroutineMock(return_value=stored_exchange),
        ) as retrieve_ex:
            exchange = await self.manager.receive_request()

            retrieve_ex.assert_called_once_with(
                self.context, connection_id, request._thread_id
            )
            save_ex.assert_called_once()

            assert exchange.state == V10CredentialExchange.STATE_REQUEST_RECEIVED
            assert exchange.credential_request == indy_cred_req

    async def test_issue_credential(self):
        connection_id = "test_conn_id"
        comment = "comment"
        cred_values = {"attr": "value"}
        indy_offer = {"schema_id": SCHEMA_ID, "cred_def_id": CRED_DEF_ID, "nonce": "0"}
        indy_cred_req = {"schema_id": SCHEMA_ID, "cred_def_id": CRED_DEF_ID}
        thread_id = "thread-id"

        stored_exchange = V10CredentialExchange(
            credential_exchange_id="dummy-cxid",
            connection_id=connection_id,
            credential_definition_id=CRED_DEF_ID,
            credential_offer=indy_offer,
            credential_request=indy_cred_req,
            credential_proposal_dict=CredentialProposal(
                credential_proposal=CredentialPreview.deserialize(
                    {"attributes": [{"name": "attr", "value": "value"}]}
                ),
                cred_def_id=CRED_DEF_ID,
                schema_id=SCHEMA_ID,
            ).serialize(),
            initiator=V10CredentialExchange.INITIATOR_SELF,
            role=V10CredentialExchange.ROLE_ISSUER,
            state=V10CredentialExchange.STATE_REQUEST_RECEIVED,
            thread_id=thread_id,
        )

        issuer = async_mock.MagicMock()
        cred = {"indy": "credential"}
        cred_rev_id = "1000"
        issuer.create_credential = async_mock.CoroutineMock(
            return_value=(json.dumps(cred), cred_rev_id)
        )
        self.context.injector.bind_instance(IndyIssuer, issuer)

        with async_mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as revoc, async_mock.patch.object(
            asyncio, "ensure_future", autospec=True
        ) as asyncio_mock, async_mock.patch.object(
            V10CredentialExchange, "save", autospec=True
        ) as save_ex:
            revoc.return_value.get_active_issuer_rev_reg_record = async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(  # active_rev_reg_rec
                    revoc_reg_id=REV_REG_ID,
                    get_registry=async_mock.CoroutineMock(
                        return_value=async_mock.MagicMock(  # rev_reg
                            tails_local_path="dummy-path",
                            get_or_fetch_local_tails_path=async_mock.CoroutineMock(),
                        )
                    ),
                )
            )
            (ret_exchange, ret_cred_issue) = await self.manager.issue_credential(
                stored_exchange, comment=comment, retries=1
            )

            save_ex.assert_called_once()

            issuer.create_credential.assert_called_once_with(
                SCHEMA,
                indy_offer,
                indy_cred_req,
                cred_values,
                stored_exchange.credential_exchange_id,
                REV_REG_ID,
                "dummy-path",
            )

            assert ret_exchange.credential == cred
            assert ret_cred_issue.indy_credential() == cred
            assert ret_exchange.state == V10CredentialExchange.STATE_ISSUED
            assert ret_cred_issue._thread_id == thread_id

            # cover case with existing cred
            stored_exchange.credential = cred
            stored_exchange.state = V10CredentialExchange.STATE_REQUEST_RECEIVED
            (
                ret_existing_exchange,
                ret_existing_cred,
            ) = await self.manager.issue_credential(
                stored_exchange, comment=comment, retries=0
            )
            assert ret_existing_exchange == ret_exchange
            assert ret_existing_cred._thread_id == thread_id

    async def test_issue_credential_non_revocable(self):
        CRED_DEF_NR = deepcopy(CRED_DEF)
        CRED_DEF_NR["value"]["revocation"] = None
        connection_id = "test_conn_id"
        comment = "comment"
        cred_values = {"attr": "value"}
        indy_offer = {"schema_id": SCHEMA_ID, "cred_def_id": CRED_DEF_ID, "nonce": "0"}
        indy_cred_req = {"schema_id": SCHEMA_ID, "cred_def_id": CRED_DEF_ID}
        thread_id = "thread-id"

        stored_exchange = V10CredentialExchange(
            credential_exchange_id="dummy-cxid",
            connection_id=connection_id,
            credential_definition_id=CRED_DEF_ID,
            credential_offer=indy_offer,
            credential_request=indy_cred_req,
            credential_proposal_dict=CredentialProposal(
                credential_proposal=CredentialPreview.deserialize(
                    {"attributes": [{"name": "attr", "value": "value"}]}
                ),
                cred_def_id=CRED_DEF_ID,
                schema_id=SCHEMA_ID,
            ).serialize(),
            initiator=V10CredentialExchange.INITIATOR_SELF,
            role=V10CredentialExchange.ROLE_ISSUER,
            state=V10CredentialExchange.STATE_REQUEST_RECEIVED,
            thread_id=thread_id,
        )

        issuer = async_mock.MagicMock()
        cred = {"indy": "credential"}
        issuer.create_credential = async_mock.CoroutineMock(
            return_value=(json.dumps(cred), None)
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
            V10CredentialExchange, "save", autospec=True
        ) as save_ex:
            (ret_exchange, ret_cred_issue) = await self.manager.issue_credential(
                stored_exchange, comment=comment, retries=0
            )

            save_ex.assert_called_once()

            issuer.create_credential.assert_called_once_with(
                SCHEMA,
                indy_offer,
                indy_cred_req,
                cred_values,
                stored_exchange.credential_exchange_id,
                None,
                None,
            )

            assert ret_exchange.credential == cred
            assert ret_cred_issue.indy_credential() == cred
            assert ret_exchange.state == V10CredentialExchange.STATE_ISSUED
            assert ret_cred_issue._thread_id == thread_id

    async def test_issue_credential_fills_rr(self):
        connection_id = "test_conn_id"
        comment = "comment"
        cred_values = {"attr": "value"}
        indy_offer = {"schema_id": SCHEMA_ID, "cred_def_id": CRED_DEF_ID, "nonce": "0"}
        indy_cred_req = {"schema_id": SCHEMA_ID, "cred_def_id": CRED_DEF_ID}
        thread_id = "thread-id"

        stored_exchange = V10CredentialExchange(
            credential_exchange_id="dummy-cxid",
            connection_id=connection_id,
            credential_definition_id=CRED_DEF_ID,
            credential_offer=indy_offer,
            credential_request=indy_cred_req,
            credential_proposal_dict=CredentialProposal(
                credential_proposal=CredentialPreview.deserialize(
                    {"attributes": [{"name": "attr", "value": "value"}]}
                ),
                cred_def_id=CRED_DEF_ID,
                schema_id=SCHEMA_ID,
            ).serialize(),
            initiator=V10CredentialExchange.INITIATOR_SELF,
            role=V10CredentialExchange.ROLE_ISSUER,
            state=V10CredentialExchange.STATE_REQUEST_RECEIVED,
            thread_id=thread_id,
            revocation_id="1000",
        )

        issuer = async_mock.MagicMock()
        cred = {"indy": "credential"}
        issuer.create_credential = async_mock.CoroutineMock(
            return_value=(json.dumps(cred), stored_exchange.revocation_id)
        )
        self.context.injector.bind_instance(IndyIssuer, issuer)

        with async_mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as revoc, async_mock.patch.object(
            asyncio, "ensure_future", autospec=True
        ) as asyncio_mock, async_mock.patch.object(
            V10CredentialExchange, "save", autospec=True
        ) as save_ex:
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
            (ret_exchange, ret_cred_issue) = await self.manager.issue_credential(
                stored_exchange, comment=comment, retries=0
            )

            save_ex.assert_called_once()

            issuer.create_credential.assert_called_once_with(
                SCHEMA,
                indy_offer,
                indy_cred_req,
                cred_values,
                stored_exchange.credential_exchange_id,
                REV_REG_ID,
                "dummy-path",
            )

            assert ret_exchange.credential == cred
            assert ret_cred_issue.indy_credential() == cred
            assert ret_exchange.state == V10CredentialExchange.STATE_ISSUED
            assert ret_cred_issue._thread_id == thread_id

    async def test_issue_credential_request_bad_state(self):
        connection_id = "test_conn_id"
        indy_offer = {"schema_id": SCHEMA_ID, "cred_def_id": CRED_DEF_ID}
        thread_id = "thread-id"

        stored_exchange = V10CredentialExchange(
            credential_exchange_id="dummy-cxid",
            connection_id=connection_id,
            credential_definition_id=CRED_DEF_ID,
            credential_offer=indy_offer,
            initiator=V10CredentialExchange.INITIATOR_SELF,
            role=V10CredentialExchange.ROLE_HOLDER,
            state=V10CredentialExchange.STATE_PROPOSAL_SENT,
            schema_id=SCHEMA_ID,
            thread_id=thread_id,
        )

        with self.assertRaises(CredentialManagerError):
            await self.manager.issue_credential(stored_exchange)

    async def test_issue_credential_no_active_rr_no_retries(self):
        connection_id = "test_conn_id"
        comment = "comment"
        cred_values = {"attr": "value"}
        indy_offer = {"schema_id": SCHEMA_ID, "cred_def_id": CRED_DEF_ID, "nonce": "0"}
        indy_cred_req = {"schema_id": SCHEMA_ID, "cred_def_id": CRED_DEF_ID}
        thread_id = "thread-id"

        stored_exchange = V10CredentialExchange(
            credential_exchange_id="dummy-cxid",
            connection_id=connection_id,
            credential_definition_id=CRED_DEF_ID,
            credential_offer=indy_offer,
            credential_request=indy_cred_req,
            credential_proposal_dict=CredentialProposal(
                credential_proposal=CredentialPreview.deserialize(
                    {"attributes": [{"name": "attr", "value": "value"}]}
                ),
                cred_def_id=CRED_DEF_ID,
                schema_id=SCHEMA_ID,
            ).serialize(),
            initiator=V10CredentialExchange.INITIATOR_SELF,
            role=V10CredentialExchange.ROLE_ISSUER,
            state=V10CredentialExchange.STATE_REQUEST_RECEIVED,
            thread_id=thread_id,
        )

        issuer = async_mock.MagicMock()
        cred = {"indy": "credential"}
        cred_rev_id = "1"
        issuer.create_credential = async_mock.CoroutineMock(
            return_value=(json.dumps(cred), cred_rev_id)
        )
        self.context.injector.bind_instance(IndyIssuer, issuer)

        with async_mock.patch.object(
            test_module, "IssuerRevRegRecord", autospec=True
        ) as issuer_rr_rec, async_mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as revoc, async_mock.patch.object(
            V10CredentialExchange, "save", autospec=True
        ) as save_ex:
            revoc.return_value.get_active_issuer_rev_reg_record = (
                async_mock.CoroutineMock(side_effect=test_module.StorageNotFoundError())
            )
            revoc.return_value.init_issuer_registry = async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(  # pending_rev_reg_rec
                    stage_pending_registry=async_mock.CoroutineMock()
                )
            )
            issuer_rr_rec.query_by_cred_def_id = async_mock.CoroutineMock(
                return_value=[]
            )
            with self.assertRaises(CredentialManagerError) as x_cred_mgr:
                await self.manager.issue_credential(
                    stored_exchange, comment=comment, retries=0
                )
                assert "has no active revocation registry" in x_cred_mgr.message

    async def test_issue_credential_no_active_rr_retry(self):
        connection_id = "test_conn_id"
        comment = "comment"
        cred_values = {"attr": "value"}
        indy_offer = {"schema_id": SCHEMA_ID, "cred_def_id": CRED_DEF_ID, "nonce": "0"}
        indy_cred_req = {"schema_id": SCHEMA_ID, "cred_def_id": CRED_DEF_ID}
        thread_id = "thread-id"

        stored_exchange = V10CredentialExchange(
            credential_exchange_id="dummy-cxid",
            connection_id=connection_id,
            credential_definition_id=CRED_DEF_ID,
            credential_offer=indy_offer,
            credential_request=indy_cred_req,
            credential_proposal_dict=CredentialProposal(
                credential_proposal=CredentialPreview.deserialize(
                    {"attributes": [{"name": "attr", "value": "value"}]}
                ),
                cred_def_id=CRED_DEF_ID,
                schema_id=SCHEMA_ID,
            ).serialize(),
            initiator=V10CredentialExchange.INITIATOR_SELF,
            role=V10CredentialExchange.ROLE_ISSUER,
            state=V10CredentialExchange.STATE_REQUEST_RECEIVED,
            thread_id=thread_id,
        )

        issuer = async_mock.MagicMock()
        cred = {"indy": "credential"}
        cred_rev_id = "1"
        issuer.create_credential = async_mock.CoroutineMock(
            return_value=(json.dumps(cred), cred_rev_id)
        )
        self.context.injector.bind_instance(IndyIssuer, issuer)

        with async_mock.patch.object(
            test_module, "IssuerRevRegRecord", autospec=True
        ) as issuer_rr_rec, async_mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as revoc, async_mock.patch.object(
            V10CredentialExchange, "save", autospec=True
        ) as save_ex:
            revoc.return_value.get_active_issuer_rev_reg_record = (
                async_mock.CoroutineMock(side_effect=test_module.StorageNotFoundError())
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
            with self.assertRaises(CredentialManagerError) as x_cred_mgr:
                await self.manager.issue_credential(
                    stored_exchange, comment=comment, retries=1
                )
                assert "has no active revocation registry" in x_cred_mgr.message

    async def test_issue_credential_rr_full(self):
        connection_id = "test_conn_id"
        comment = "comment"
        cred_values = {"attr": "value"}
        indy_offer = {"schema_id": SCHEMA_ID, "cred_def_id": CRED_DEF_ID, "nonce": "0"}
        indy_cred_req = {"schema_id": SCHEMA_ID, "cred_def_id": CRED_DEF_ID}
        thread_id = "thread-id"

        stored_exchange = V10CredentialExchange(
            credential_exchange_id="dummy-cxid",
            connection_id=connection_id,
            credential_definition_id=CRED_DEF_ID,
            credential_offer=indy_offer,
            credential_request=indy_cred_req,
            credential_proposal_dict=CredentialProposal(
                credential_proposal=CredentialPreview.deserialize(
                    {"attributes": [{"name": "attr", "value": "value"}]}
                ),
                cred_def_id=CRED_DEF_ID,
                schema_id=SCHEMA_ID,
            ).serialize(),
            initiator=V10CredentialExchange.INITIATOR_SELF,
            role=V10CredentialExchange.ROLE_ISSUER,
            state=V10CredentialExchange.STATE_REQUEST_RECEIVED,
            thread_id=thread_id,
        )

        issuer = async_mock.MagicMock()
        cred = {"indy": "credential"}
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
                    stored_exchange, comment=comment, retries=1
                )

    async def test_receive_credential(self):
        connection_id = "test_conn_id"
        indy_cred = {"indy": "credential"}

        stored_exchange = V10CredentialExchange(
            credential_exchange_id="dummy-cxid",
            connection_id=connection_id,
            initiator=V10CredentialExchange.INITIATOR_EXTERNAL,
            role=V10CredentialExchange.ROLE_ISSUER,
        )

        issue = CredentialIssue(
            credentials_attach=[CredentialIssue.wrap_indy_credential(indy_cred)]
        )
        self.context.message = issue
        self.context.connection_record = async_mock.MagicMock()
        self.context.connection_record.connection_id = connection_id

        with async_mock.patch.object(
            V10CredentialExchange, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            V10CredentialExchange,
            "retrieve_by_connection_and_thread",
            async_mock.CoroutineMock(return_value=stored_exchange),
        ) as retrieve_ex:
            exchange = await self.manager.receive_credential()

            retrieve_ex.assert_called_once_with(
                self.context, connection_id, issue._thread_id
            )
            save_ex.assert_called_once()

            assert exchange.raw_credential == indy_cred
            assert exchange.state == V10CredentialExchange.STATE_CREDENTIAL_RECEIVED

    async def test_store_credential(self):
        connection_id = "test_conn_id"
        cred = {"cred_def_id": CRED_DEF_ID, "rev_reg_id": REV_REG_ID}
        cred_req_meta = {"req": "meta"}
        thread_id = "thread-id"

        stored_exchange = V10CredentialExchange(
            credential_exchange_id="dummy-cxid",
            connection_id=connection_id,
            credential_definition_id=CRED_DEF_ID,
            credential_request_metadata=cred_req_meta,
            credential_proposal_dict={"credential_proposal": {}},
            raw_credential=cred,
            initiator=V10CredentialExchange.INITIATOR_EXTERNAL,
            role=V10CredentialExchange.ROLE_HOLDER,
            state=V10CredentialExchange.STATE_CREDENTIAL_RECEIVED,
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
            V10CredentialExchange, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            V10CredentialExchange, "delete_record", autospec=True
        ) as delete_ex, async_mock.patch.object(
            CredentialPreview, "deserialize", autospec=True
        ) as mock_preview_deserialize:

            mock_rev_reg.from_definition = async_mock.MagicMock(
                return_value=async_mock.MagicMock(
                    get_or_fetch_local_tails_path=async_mock.CoroutineMock()
                )
            )
            ret_exchange, ret_cred_ack = await self.manager.store_credential(
                stored_exchange, credential_id=cred_id
            )

            save_ex.assert_called_once()

            self.ledger.get_credential_definition.assert_called_once_with(CRED_DEF_ID)

            holder.store_credential.assert_called_once_with(
                CRED_DEF,
                cred,
                cred_req_meta,
                mock_preview_deserialize.return_value.mime_types.return_value,
                credential_id=cred_id,
                rev_reg_def=REV_REG_DEF,
            )

            holder.get_credential.assert_called_once_with(cred_id)

            assert ret_exchange.credential_id == cred_id
            assert ret_exchange.credential == stored_cred
            assert ret_exchange.state == V10CredentialExchange.STATE_ACKED
            assert ret_cred_ack._thread_id == thread_id

    async def test_store_credential_bad_state(self):
        connection_id = "test_conn_id"
        cred = {"cred_def_id": CRED_DEF_ID}
        cred_req_meta = {"req": "meta"}
        thread_id = "thread-id"

        stored_exchange = V10CredentialExchange(
            credential_exchange_id="dummy-cxid",
            connection_id=connection_id,
            credential_definition_id=CRED_DEF_ID,
            credential_request_metadata=cred_req_meta,
            credential_proposal_dict=None,
            raw_credential=cred,
            initiator=V10CredentialExchange.INITIATOR_EXTERNAL,
            role=V10CredentialExchange.ROLE_HOLDER,
            state=V10CredentialExchange.STATE_OFFER_RECEIVED,
            thread_id=thread_id,
        )
        cred_id = "cred-id"

        with self.assertRaises(CredentialManagerError):
            await self.manager.store_credential(stored_exchange, credential_id=cred_id)

    async def test_store_credential_no_preview(self):
        connection_id = "test_conn_id"
        cred = {"cred_def_id": CRED_DEF_ID}
        cred_req_meta = {"req": "meta"}
        thread_id = "thread-id"

        stored_exchange = V10CredentialExchange(
            credential_exchange_id="dummy-cxid",
            connection_id=connection_id,
            credential_definition_id=CRED_DEF_ID,
            credential_request_metadata=cred_req_meta,
            credential_proposal_dict=None,
            raw_credential=cred,
            initiator=V10CredentialExchange.INITIATOR_EXTERNAL,
            role=V10CredentialExchange.ROLE_HOLDER,
            state=V10CredentialExchange.STATE_CREDENTIAL_RECEIVED,
            thread_id=thread_id,
        )

        cred_def = async_mock.MagicMock()
        self.ledger.get_credential_definition = async_mock.CoroutineMock(
            return_value=cred_def
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
            V10CredentialExchange, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            V10CredentialExchange, "delete_record", autospec=True
        ) as delete_ex:
            ret_exchange, ret_cred_ack = await self.manager.store_credential(
                stored_exchange
            )

            save_ex.assert_called_once()

            self.ledger.get_credential_definition.assert_called_once_with(CRED_DEF_ID)

            holder.store_credential.assert_called_once_with(
                cred_def,
                cred,
                cred_req_meta,
                None,
                credential_id=None,
                rev_reg_def=None,
            )

            holder.get_credential.assert_called_once_with(cred_id)

            assert ret_exchange.credential_id == cred_id
            assert ret_exchange.credential == stored_cred
            assert ret_exchange.state == V10CredentialExchange.STATE_ACKED
            assert ret_cred_ack._thread_id == thread_id

    async def test_store_credential_holder_store_indy_error(self):
        connection_id = "test_conn_id"
        cred = {"cred_def_id": CRED_DEF_ID}
        cred_req_meta = {"req": "meta"}
        thread_id = "thread-id"

        stored_exchange = V10CredentialExchange(
            credential_exchange_id="dummy-cxid",
            connection_id=connection_id,
            credential_definition_id=CRED_DEF_ID,
            credential_request_metadata=cred_req_meta,
            credential_proposal_dict=None,
            raw_credential=cred,
            initiator=V10CredentialExchange.INITIATOR_EXTERNAL,
            role=V10CredentialExchange.ROLE_HOLDER,
            state=V10CredentialExchange.STATE_CREDENTIAL_RECEIVED,
            thread_id=thread_id,
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

        with self.assertRaises(test_module.IndyHolderError):
            await self.manager.store_credential(
                cred_ex_record=stored_exchange, credential_id=cred_id
            )

    async def test_credential_ack(self):
        connection_id = "connection-id"
        stored_exchange = V10CredentialExchange(
            credential_exchange_id="dummy-cxid",
            connection_id=connection_id,
            initiator=V10CredentialExchange.INITIATOR_SELF,
            role=V10CredentialExchange.ROLE_ISSUER,
        )

        ack = CredentialAck()
        self.context.message = ack
        self.context.connection_record = async_mock.MagicMock()
        self.context.connection_record.connection_id = connection_id

        with async_mock.patch.object(
            V10CredentialExchange, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            V10CredentialExchange, "delete_record", autospec=True
        ) as delete_ex, async_mock.patch.object(
            V10CredentialExchange,
            "retrieve_by_connection_and_thread",
            async_mock.CoroutineMock(return_value=stored_exchange),
        ) as retrieve_ex:
            ret_exchange = await self.manager.receive_credential_ack()

            retrieve_ex.assert_called_once_with(
                self.context, connection_id, ack._thread_id
            )
            save_ex.assert_called_once()

            assert ret_exchange.state == V10CredentialExchange.STATE_ACKED
            delete_ex.assert_called_once()

    async def test_retrieve_records(self):
        self.cache = BasicCache()
        self.context.injector.bind_instance(BaseCache, self.cache)

        self.storage = BasicStorage()
        self.context.injector.bind_instance(BaseStorage, self.storage)
        storage: BaseStorage =  self.context.inject(BaseStorage)
        for index in range(2):
            exchange_record = V10CredentialExchange(
                connection_id=str(index),
                thread_id=str(1000 + index),
                initiator=V10CredentialExchange.INITIATOR_SELF,
                role=V10CredentialExchange.ROLE_ISSUER,
            )
            await exchange_record.save(self.context)

        for i in range(2):  # second pass gets from cache
            for index in range(2):
                ret_ex = await V10CredentialExchange.retrieve_by_connection_and_thread(
                    self.context, str(index), str(1000 + index)
                )
                assert ret_ex.connection_id == str(index)
                assert ret_ex.thread_id == str(1000 + index)
