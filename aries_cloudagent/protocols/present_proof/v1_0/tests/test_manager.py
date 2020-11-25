import json

from time import time

from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from .....config.injection_context import InjectionContext
from .....indy.holder import IndyHolder
from .....indy.sdk.holder import IndySdkHolder
from .....indy.issuer import IndyIssuer
from .....ledger.base import BaseLedger
from .....messaging.request_context import RequestContext
from .....messaging.responder import BaseResponder, MockResponder
from .....storage.error import StorageNotFoundError
from .....indy.verifier import IndyVerifier
from .....indy.sdk.verifier import IndySdkVerifier

from ....didcomm_prefix import DIDCommPrefix

from .. import manager as test_module
from ..manager import PresentationManager, PresentationManagerError
from ..messages.presentation import Presentation
from ..messages.presentation_ack import PresentationAck
from ..messages.presentation_proposal import PresentationProposal
from ..messages.presentation_request import PresentationRequest
from ..messages.inner.presentation_preview import (
    PresAttrSpec,
    PresentationPreview,
    PresPredSpec,
)
from ..models.presentation_exchange import V10PresentationExchange
from ..util.indy import indy_proof_req_preview2indy_requested_creds


CONN_ID = "connection_id"
ISSUER_DID = "NcYxiDXkpYi6ov5FcYDi1e"
S_ID = f"{ISSUER_DID}:2:vidya:1.0"
CD_ID = f"{ISSUER_DID}:3:CL:{S_ID}:tag1"
RR_ID = f"{ISSUER_DID}:4:{CD_ID}:CL_ACCUM:0"
PRES_PREVIEW = PresentationPreview(
    attributes=[
        PresAttrSpec(name="player", cred_def_id=CD_ID, value="Richie Knucklez"),
        PresAttrSpec(
            name="screenCapture",
            cred_def_id=CD_ID,
            mime_type="image/png",
            value="aW1hZ2luZSBhIHNjcmVlbiBjYXB0dXJl",
        ),
    ],
    predicates=[
        PresPredSpec(
            name="highScore", cred_def_id=CD_ID, predicate=">=", threshold=1000000
        )
    ],
)
PRES_PREVIEW_NAMES = PresentationPreview(
    attributes=[
        PresAttrSpec(
            name="player", cred_def_id=CD_ID, value="Richie Knucklez", referent="0"
        ),
        PresAttrSpec(
            name="screenCapture",
            cred_def_id=CD_ID,
            mime_type="image/png",
            value="aW1hZ2luZSBhIHNjcmVlbiBjYXB0dXJl",
            referent="0",
        ),
    ],
    predicates=[
        PresPredSpec(
            name="highScore", cred_def_id=CD_ID, predicate=">=", threshold=1000000
        )
    ],
)
PROOF_REQ_NAME = "name"
PROOF_REQ_VERSION = "1.0"
PROOF_REQ_NONCE = "12345"

NOW = int(time())


class TestPresentationManager(AsyncTestCase):
    async def setUp(self):
        self.context = RequestContext(
            base_context=InjectionContext(enforce_typing=False)
        )

        Ledger = async_mock.MagicMock(BaseLedger, autospec=True)
        self.ledger = Ledger()
        self.ledger.get_schema = async_mock.CoroutineMock(
            return_value=async_mock.MagicMock()
        )
        self.ledger.get_credential_definition = async_mock.CoroutineMock(
            return_value={"value": {"revocation": {"...": "..."}}}
        )
        self.ledger.get_revoc_reg_def = async_mock.CoroutineMock(
            return_value={
                "ver": "1.0",
                "id": RR_ID,
                "revocDefType": "CL_ACCUM",
                "tag": RR_ID.split(":")[-1],
                "credDefId": CD_ID,
                "value": {
                    "IssuanceType": "ISSUANCE_BY_DEFAULT",
                    "maxCredNum": 1000,
                    "publicKeys": {"accumKey": {"z": "1 ..."}},
                    "tailsHash": "3MLjUFQz9x9n5u9rFu8Ba9C5bo4HNFjkPNc54jZPSNaZ",
                    "tailsLocation": "http://sample.ca/path",
                },
            }
        )
        self.ledger.get_revoc_reg_delta = async_mock.CoroutineMock(
            return_value=(
                {
                    "ver": "1.0",
                    "value": {"prevAccum": "1 ...", "accum": "21 ...", "issued": [1]},
                },
                NOW,
            )
        )
        self.ledger.get_revoc_reg_entry = async_mock.CoroutineMock(
            return_value=(
                {
                    "ver": "1.0",
                    "value": {"prevAccum": "1 ...", "accum": "21 ...", "issued": [1]},
                },
                NOW,
            )
        )
        self.context.injector.bind_instance(BaseLedger, self.ledger)

        Holder = async_mock.MagicMock(IndyHolder, autospec=True)
        self.holder = Holder()
        get_creds = async_mock.CoroutineMock(
            return_value=(
                {
                    "cred_info": {
                        "referent": "dummy_reft",
                        "attrs": {
                            "player": "Richie Knucklez",
                            "screenCapture": "aW1hZ2luZSBhIHNjcmVlbiBjYXB0dXJl",
                            "highScore": "1234560",
                        },
                    }
                },  # leave this comma: return a tuple
            )
        )
        self.holder.get_credentials_for_presentation_request_by_referent = get_creds
        self.holder.get_credential = async_mock.CoroutineMock(
            return_value=json.dumps(
                {
                    "schema_id": S_ID,
                    "cred_def_id": CD_ID,
                    "rev_reg_id": RR_ID,
                    "cred_rev_id": 1,
                }
            )
        )
        self.holder.create_presentation = async_mock.CoroutineMock(return_value="{}")
        self.holder.create_revocation_state = async_mock.CoroutineMock(
            return_value=json.dumps(
                {
                    "witness": {"omega": "1 ..."},
                    "rev_reg": {"accum": "21 ..."},
                    "timestamp": NOW,
                }
            )
        )
        self.context.injector.bind_instance(IndyHolder, self.holder)

        Verifier = async_mock.MagicMock(IndyVerifier, autospec=True)
        self.verifier = Verifier()
        self.verifier.verify_presentation = async_mock.CoroutineMock(
            return_value="true"
        )
        self.context.injector.bind_instance(IndyVerifier, self.verifier)

        self.manager = PresentationManager(self.context)

    async def test_record_eq(self):
        same = [
            V10PresentationExchange(
                presentation_exchange_id="dummy-0",
                thread_id="thread-0",
                role=V10PresentationExchange.ROLE_PROVER,
            )
        ] * 2
        diff = [
            V10PresentationExchange(
                presentation_exchange_id="dummy-1",
                role=V10PresentationExchange.ROLE_PROVER,
            ),
            V10PresentationExchange(
                presentation_exchange_id="dummy-0",
                thread_id="thread-1",
                role=V10PresentationExchange.ROLE_PROVER,
            ),
            V10PresentationExchange(
                presentation_exchange_id="dummy-1",
                thread_id="thread-0",
                role=V10PresentationExchange.ROLE_VERIFIER,
            ),
        ]

        for i in range(len(same) - 1):
            for j in range(i, len(same)):
                assert same[i] == same[j]

        for i in range(len(diff) - 1):
            for j in range(i, len(diff)):
                assert diff[i] == diff[j] if i == j else diff[i] != diff[j]

    async def test_create_exchange_for_proposal(self):
        self.context.connection_record = async_mock.MagicMock()
        self.context.connection_record.connection_id = CONN_ID

        proposal = PresentationProposal()
        self.context.message = proposal

        with async_mock.patch.object(
            V10PresentationExchange, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            PresentationProposal, "serialize", autospec=True
        ):
            exchange = await self.manager.create_exchange_for_proposal(
                CONN_ID, proposal, auto_present=None
            )
            save_ex.assert_called_once()

            assert exchange.thread_id == proposal._thread_id
            assert exchange.initiator == V10PresentationExchange.INITIATOR_SELF
            assert exchange.role == V10PresentationExchange.ROLE_PROVER
            assert exchange.state == V10PresentationExchange.STATE_PROPOSAL_SENT

    async def test_receive_proposal(self):
        self.context.connection_record = async_mock.MagicMock()
        self.context.connection_record.connection_id = CONN_ID

        proposal = PresentationProposal()
        self.context.message = proposal

        with async_mock.patch.object(
            V10PresentationExchange, "save", autospec=True
        ) as save_ex:
            exchange = await self.manager.receive_proposal()
            save_ex.assert_called_once()

            assert exchange.state == V10PresentationExchange.STATE_PROPOSAL_RECEIVED

    async def test_create_bound_request(self):
        comment = "comment"

        proposal = PresentationProposal(presentation_proposal=PRES_PREVIEW)
        exchange = V10PresentationExchange(
            presentation_proposal_dict=proposal.serialize(),
            role=V10PresentationExchange.ROLE_VERIFIER,
        )
        exchange.save = async_mock.CoroutineMock()
        (ret_exchange, pres_req_msg) = await self.manager.create_bound_request(
            presentation_exchange_record=exchange,
            name=PROOF_REQ_NAME,
            version=PROOF_REQ_VERSION,
            nonce=PROOF_REQ_NONCE,
            comment=comment,
        )
        assert ret_exchange is exchange
        exchange.save.assert_called_once()

    async def test_create_exchange_for_request(self):
        self.context.connection_record = async_mock.MagicMock()
        self.context.connection_record.connection_id = CONN_ID

        request = async_mock.MagicMock()
        request.indy_proof_request = async_mock.MagicMock()
        request._thread_id = "dummy"
        self.context.message = request

        with async_mock.patch.object(
            V10PresentationExchange, "save", autospec=True
        ) as save_ex:
            exchange = await self.manager.create_exchange_for_request(CONN_ID, request)
            save_ex.assert_called_once()

            assert exchange.thread_id == request._thread_id
            assert exchange.initiator == V10PresentationExchange.INITIATOR_SELF
            assert exchange.role == V10PresentationExchange.ROLE_VERIFIER
            assert exchange.state == V10PresentationExchange.STATE_REQUEST_SENT

    async def test_receive_request(self):
        self.context.connection_record = async_mock.MagicMock()
        self.context.connection_record.connection_id = CONN_ID

        request = PresentationRequest()
        self.context.message = request

        exchange_in = V10PresentationExchange()

        with async_mock.patch.object(
            V10PresentationExchange, "save", autospec=True
        ) as save_ex:
            exchange_out = await self.manager.receive_request(exchange_in)
            save_ex.assert_called_once()

            assert exchange_out.state == V10PresentationExchange.STATE_REQUEST_RECEIVED

    async def test_create_presentation(self):
        self.context.connection_record = async_mock.MagicMock()
        self.context.connection_record.connection_id = CONN_ID

        exchange_in = V10PresentationExchange()
        indy_proof_req = await PRES_PREVIEW.indy_proof_request(
            name=PROOF_REQ_NAME,
            version=PROOF_REQ_VERSION,
            nonce=PROOF_REQ_NONCE,
            ledger=self.context.inject(BaseLedger, required=False),
        )

        exchange_in.presentation_request = indy_proof_req
        request = async_mock.MagicMock()
        request.indy_proof_request = async_mock.MagicMock()
        request._thread_id = "dummy"
        self.context.message = request

        more_magic_rr = async_mock.MagicMock(
            get_or_fetch_local_tails_path=async_mock.CoroutineMock(
                return_value="/tmp/sample/tails/path"
            )
        )
        with async_mock.patch.object(
            V10PresentationExchange, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            test_module, "AttachDecorator", autospec=True
        ) as mock_attach_decorator, async_mock.patch.object(
            test_module, "RevocationRegistry", autospec=True
        ) as mock_rr:
            mock_rr.from_definition = async_mock.MagicMock(return_value=more_magic_rr)

            mock_attach_decorator.from_indy_dict = async_mock.MagicMock(
                return_value=mock_attach_decorator
            )

            req_creds = await indy_proof_req_preview2indy_requested_creds(
                indy_proof_req, holder=self.holder
            )
            assert not req_creds["self_attested_attributes"]
            assert len(req_creds["requested_attributes"]) == 2
            assert len(req_creds["requested_predicates"]) == 1

            (exchange_out, pres_msg) = await self.manager.create_presentation(
                exchange_in, req_creds
            )
            save_ex.assert_called_once()
            assert exchange_out.state == V10PresentationExchange.STATE_PRESENTATION_SENT

    async def test_create_presentation_proof_req_non_revoc_interval_none(self):
        self.context.connection_record = async_mock.MagicMock()
        self.context.connection_record.connection_id = CONN_ID

        exchange_in = V10PresentationExchange()
        indy_proof_req = await PRES_PREVIEW.indy_proof_request(
            name=PROOF_REQ_NAME,
            version=PROOF_REQ_VERSION,
            nonce=PROOF_REQ_NONCE,
            ledger=self.context.inject(BaseLedger, required=False),
        )
        indy_proof_req["non_revoked"] = None  # simulate interop with indy-vcx

        exchange_in.presentation_request = indy_proof_req
        request = async_mock.MagicMock()
        request.indy_proof_request = async_mock.MagicMock()
        request._thread_id = "dummy"
        self.context.message = request

        more_magic_rr = async_mock.MagicMock(
            get_or_fetch_local_tails_path=async_mock.CoroutineMock(
                return_value="/tmp/sample/tails/path"
            )
        )
        with async_mock.patch.object(
            V10PresentationExchange, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            test_module, "AttachDecorator", autospec=True
        ) as mock_attach_decorator, async_mock.patch.object(
            test_module, "RevocationRegistry", autospec=True
        ) as mock_rr:
            mock_rr.from_definition = async_mock.MagicMock(return_value=more_magic_rr)

            mock_attach_decorator.from_indy_dict = async_mock.MagicMock(
                return_value=mock_attach_decorator
            )

            req_creds = await indy_proof_req_preview2indy_requested_creds(
                indy_proof_req, holder=self.holder
            )
            assert not req_creds["self_attested_attributes"]
            assert len(req_creds["requested_attributes"]) == 2
            assert len(req_creds["requested_predicates"]) == 1

            (exchange_out, pres_msg) = await self.manager.create_presentation(
                exchange_in, req_creds
            )
            save_ex.assert_called_once()
            assert exchange_out.state == V10PresentationExchange.STATE_PRESENTATION_SENT

    async def test_create_presentation_self_asserted(self):
        self.context.connection_record = async_mock.MagicMock()
        self.context.connection_record.connection_id = CONN_ID
        PRES_PREVIEW_SELFIE = PresentationPreview(
            attributes=[
                PresAttrSpec(name="player", value="Richie Knucklez"),
                PresAttrSpec(
                    name="screenCapture",
                    mime_type="image/png",
                    value="aW1hZ2luZSBhIHNjcmVlbiBjYXB0dXJl",
                ),
            ],
            predicates=[
                PresPredSpec(
                    name="highScore",
                    cred_def_id=None,
                    predicate=">=",
                    threshold=1000000,
                )
            ],
        )

        exchange_in = V10PresentationExchange()
        indy_proof_req = await PRES_PREVIEW_SELFIE.indy_proof_request(
            name=PROOF_REQ_NAME,
            version=PROOF_REQ_VERSION,
            nonce=PROOF_REQ_NONCE,
            ledger=self.context.inject(BaseLedger, required=False),
        )

        exchange_in.presentation_request = indy_proof_req
        request = async_mock.MagicMock()
        request.indy_proof_request = async_mock.MagicMock()
        request._thread_id = "dummy"
        self.context.message = request

        more_magic_rr = async_mock.MagicMock(
            get_or_fetch_local_tails_path=async_mock.CoroutineMock(
                return_value="/tmp/sample/tails/path"
            )
        )
        with async_mock.patch.object(
            V10PresentationExchange, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            test_module, "AttachDecorator", autospec=True
        ) as mock_attach_decorator, async_mock.patch.object(
            test_module, "RevocationRegistry", autospec=True
        ) as mock_rr:
            mock_rr.from_definition = async_mock.MagicMock(return_value=more_magic_rr)

            mock_attach_decorator.from_indy_dict = async_mock.MagicMock(
                return_value=mock_attach_decorator
            )

            req_creds = await indy_proof_req_preview2indy_requested_creds(
                indy_proof_req, holder=self.holder
            )
            assert len(req_creds["self_attested_attributes"]) == 3
            assert not req_creds["requested_attributes"]
            assert not req_creds["requested_predicates"]

            (exchange_out, pres_msg) = await self.manager.create_presentation(
                exchange_in, req_creds
            )
            save_ex.assert_called_once()
            assert exchange_out.state == V10PresentationExchange.STATE_PRESENTATION_SENT

    async def test_create_presentation_no_revocation(self):
        self.context.connection_record = async_mock.MagicMock()
        self.context.connection_record.connection_id = CONN_ID

        Ledger = async_mock.MagicMock(BaseLedger, autospec=True)
        self.ledger = Ledger()
        self.ledger.get_schema = async_mock.CoroutineMock(
            return_value=async_mock.MagicMock()
        )
        self.ledger.get_credential_definition = async_mock.CoroutineMock(
            return_value={"value": {"revocation": None}}
        )
        self.context.injector.clear_binding(BaseLedger)
        self.context.injector.bind_instance(BaseLedger, self.ledger)

        exchange_in = V10PresentationExchange()
        indy_proof_req = await PRES_PREVIEW.indy_proof_request(
            name=PROOF_REQ_NAME,
            version=PROOF_REQ_VERSION,
            nonce=PROOF_REQ_NONCE,
            ledger=self.context.inject(BaseLedger, required=False),
        )

        exchange_in.presentation_request = indy_proof_req
        request = async_mock.MagicMock()
        request.indy_proof_request = async_mock.MagicMock()
        request._thread_id = "dummy"
        self.context.message = request

        Holder = async_mock.MagicMock(IndyHolder, autospec=True)
        self.holder = Holder()
        get_creds = async_mock.CoroutineMock(
            return_value=(
                {
                    "cred_info": {"referent": "dummy_reft"},
                    "attrs": {
                        "player": "Richie Knucklez",
                        "screenCapture": "aW1hZ2luZSBhIHNjcmVlbiBjYXB0dXJl",
                        "highScore": "1234560",
                    },
                },  # leave this comma: return a tuple
            )
        )
        self.holder.get_credentials_for_presentation_request_by_referent = get_creds
        self.holder.get_credential = async_mock.CoroutineMock(
            return_value=json.dumps(
                {
                    "schema_id": S_ID,
                    "cred_def_id": CD_ID,
                    "rev_reg_id": None,
                    "cred_rev_id": None,
                }
            )
        )
        self.holder.create_presentation = async_mock.CoroutineMock(return_value="{}")
        self.context.injector.clear_binding(IndyHolder)
        self.context.injector.bind_instance(IndyHolder, self.holder)

        with async_mock.patch.object(
            V10PresentationExchange, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            test_module, "AttachDecorator", autospec=True
        ) as mock_attach_decorator:

            mock_attach_decorator.from_indy_dict = async_mock.MagicMock(
                return_value=mock_attach_decorator
            )

            req_creds = await indy_proof_req_preview2indy_requested_creds(
                indy_proof_req, holder=self.holder
            )

            (exchange_out, pres_msg) = await self.manager.create_presentation(
                exchange_in, req_creds
            )
            save_ex.assert_called_once()
            assert exchange_out.state == V10PresentationExchange.STATE_PRESENTATION_SENT

    async def test_create_presentation_bad_revoc_state(self):
        self.context.connection_record = async_mock.MagicMock()
        self.context.connection_record.connection_id = CONN_ID

        exchange_in = V10PresentationExchange()
        indy_proof_req = await PRES_PREVIEW.indy_proof_request(
            name=PROOF_REQ_NAME,
            version=PROOF_REQ_VERSION,
            nonce=PROOF_REQ_NONCE,
            ledger=self.context.inject(BaseLedger, required=False),
        )

        exchange_in.presentation_request = indy_proof_req
        request = async_mock.MagicMock()
        request.indy_proof_request = async_mock.MagicMock()
        request._thread_id = "dummy"
        self.context.message = request

        Holder = async_mock.MagicMock(IndyHolder, autospec=True)
        self.holder = Holder()
        get_creds = async_mock.CoroutineMock(
            return_value=(
                {
                    "cred_info": {"referent": "dummy_reft"},
                    "attrs": {
                        "player": "Richie Knucklez",
                        "screenCapture": "aW1hZ2luZSBhIHNjcmVlbiBjYXB0dXJl",
                        "highScore": "1234560",
                    },
                },  # leave this comma: return a tuple
            )
        )
        self.holder.get_credentials_for_presentation_request_by_referent = get_creds

        self.holder.get_credential = async_mock.CoroutineMock(
            return_value=json.dumps(
                {
                    "schema_id": S_ID,
                    "cred_def_id": CD_ID,
                    "rev_reg_id": RR_ID,
                    "cred_rev_id": 1,
                }
            )
        )
        self.holder.create_presentation = async_mock.CoroutineMock(return_value="{}")
        self.holder.create_revocation_state = async_mock.CoroutineMock(
            side_effect=test_module.IndyHolderError("Problem", {"message": "Nope"})
        )
        self.context.injector.clear_binding(IndyHolder)
        self.context.injector.bind_instance(IndyHolder, self.holder)

        more_magic_rr = async_mock.MagicMock(
            get_or_fetch_local_tails_path=async_mock.CoroutineMock(
                return_value="/tmp/sample/tails/path"
            )
        )
        with async_mock.patch.object(
            V10PresentationExchange, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            test_module, "AttachDecorator", autospec=True
        ) as mock_attach_decorator, async_mock.patch.object(
            test_module, "RevocationRegistry", autospec=True
        ) as mock_rr:
            mock_rr.from_definition = async_mock.MagicMock(return_value=more_magic_rr)

            mock_attach_decorator.from_indy_dict = async_mock.MagicMock(
                return_value=mock_attach_decorator
            )

            req_creds = await indy_proof_req_preview2indy_requested_creds(
                indy_proof_req, holder=self.holder
            )

            with self.assertRaises(test_module.IndyHolderError):
                await self.manager.create_presentation(exchange_in, req_creds)

    async def test_create_presentation_multi_matching_proposal_creds_names(self):
        self.context.connection_record = async_mock.MagicMock()
        self.context.connection_record.connection_id = CONN_ID

        exchange_in = V10PresentationExchange()
        indy_proof_req = await PRES_PREVIEW_NAMES.indy_proof_request(
            name=PROOF_REQ_NAME,
            version=PROOF_REQ_VERSION,
            nonce=PROOF_REQ_NONCE,
            ledger=self.context.inject(BaseLedger, required=False),
        )

        exchange_in.presentation_request = indy_proof_req
        request = async_mock.MagicMock()
        request.indy_proof_request = async_mock.MagicMock()
        request._thread_id = "dummy"
        self.context.message = request

        Holder = async_mock.MagicMock(IndyHolder, autospec=True)
        self.holder = Holder()
        get_creds = async_mock.CoroutineMock(
            return_value=(
                {
                    "cred_info": {
                        "referent": "dummy_reft_0",
                        "cred_def_id": CD_ID,
                        "attrs": {
                            "player": "Richie Knucklez",
                            "screenCapture": "aW1hZ2luZSBhIHNjcmVlbiBjYXB0dXJl",
                            "highScore": "1234560",
                        },
                    }
                },
                {
                    "cred_info": {
                        "referent": "dummy_reft_1",
                        "cred_def_id": CD_ID,
                        "attrs": {
                            "player": "Richie Knucklez",
                            "screenCapture": "aW1hZ2luZSBhbm90aGVyIHNjcmVlbiBjYXB0dXJl",
                            "highScore": "1515880",
                        },
                    }
                },
            )
        )
        self.holder.get_credentials_for_presentation_request_by_referent = get_creds
        self.holder.get_credential = async_mock.CoroutineMock(
            return_value=json.dumps(
                {
                    "schema_id": S_ID,
                    "cred_def_id": CD_ID,
                    "rev_reg_id": RR_ID,
                    "cred_rev_id": 1,
                }
            )
        )
        self.holder.create_presentation = async_mock.CoroutineMock(return_value="{}")
        self.holder.create_revocation_state = async_mock.CoroutineMock(
            return_value=json.dumps(
                {
                    "witness": {"omega": "1 ..."},
                    "rev_reg": {"accum": "21 ..."},
                    "timestamp": NOW,
                }
            )
        )
        self.context.injector.clear_binding(IndyHolder)
        self.context.injector.bind_instance(IndyHolder, self.holder)

        more_magic_rr = async_mock.MagicMock(
            get_or_fetch_local_tails_path=async_mock.CoroutineMock(
                return_value="/tmp/sample/tails/path"
            )
        )
        with async_mock.patch.object(
            V10PresentationExchange, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            test_module, "AttachDecorator", autospec=True
        ) as mock_attach_decorator, async_mock.patch.object(
            test_module, "RevocationRegistry", autospec=True
        ) as mock_rr:
            mock_rr.from_definition = async_mock.MagicMock(return_value=more_magic_rr)

            mock_attach_decorator.from_indy_dict = async_mock.MagicMock(
                return_value=mock_attach_decorator
            )

            req_creds = await indy_proof_req_preview2indy_requested_creds(
                indy_proof_req, preview=PRES_PREVIEW_NAMES, holder=self.holder
            )
            assert not req_creds["self_attested_attributes"]
            assert len(req_creds["requested_attributes"]) == 1
            assert len(req_creds["requested_predicates"]) == 1

            (exchange_out, pres_msg) = await self.manager.create_presentation(
                exchange_in, req_creds
            )
            save_ex.assert_called_once()
            assert exchange_out.state == V10PresentationExchange.STATE_PRESENTATION_SENT

    async def test_no_matching_creds_for_proof_req(self):
        exchange_in = V10PresentationExchange()
        indy_proof_req = await PRES_PREVIEW.indy_proof_request(
            name=PROOF_REQ_NAME,
            version=PROOF_REQ_VERSION,
            nonce=PROOF_REQ_NONCE,
            ledger=self.context.inject(BaseLedger, required=False),
        )
        get_creds = async_mock.CoroutineMock(return_value=())
        self.holder.get_credentials_for_presentation_request_by_referent = get_creds

        with self.assertRaises(ValueError):
            await indy_proof_req_preview2indy_requested_creds(
                indy_proof_req, holder=self.holder
            )

        get_creds = async_mock.CoroutineMock(
            return_value=(
                {
                    "cred_info": {"referent": "dummy_reft"},
                    "attrs": {
                        "player": "Richie Knucklez",
                        "screenCapture": "aW1hZ2luZSBhIHNjcmVlbiBjYXB0dXJl",
                        "highScore": "1234560",
                    },
                },  # leave this comma: return a tuple
            )
        )
        self.holder.get_credentials_for_presentation_request_by_referent = get_creds

    async def test_receive_presentation(self):
        self.context.connection_record = async_mock.MagicMock()
        self.context.connection_record.connection_id = CONN_ID

        exchange_dummy = V10PresentationExchange(
            presentation_proposal_dict={
                "presentation_proposal": {
                    "@type": DIDCommPrefix.qualify_current(
                        "present-proof/1.0/presentation-preview"
                    ),
                    "attributes": [
                        {"name": "favourite", "cred_def_id": CD_ID, "value": "potato"},
                        {"name": "icon", "cred_def_id": CD_ID, "value": "cG90YXRv"},
                    ],
                    "predicates": [],
                }
            },
            presentation_request={
                "name": "proof-request",
                "version": "1.0",
                "nonce": "1234567890",
                "requested_attributes": {
                    "0_favourite_uuid": {
                        "name": "favourite",
                        "restrictions": [{"cred_def_id": CD_ID}],
                    },
                    "1_icon_uuid": {
                        "name": "icon",
                        "restrictions": [{"cred_def_id": CD_ID}],
                    },
                },
            },
            presentation={
                "proof": {
                    "proofs": [],
                    "requested_proof": {
                        "revealed_attrs": {
                            "0_favourite_uuid": {
                                "sub_proof_index": 0,
                                "raw": "potato",
                                "encoded": "12345678901234567890",
                            },
                            "1_icon_uuid": {
                                "sub_proof_index": 1,
                                "raw": "cG90YXRv",
                                "encoded": "12345678901234567890",
                            },
                        },
                        "self_attested_attrs": {},
                        "unrevealed_attrs": {},
                        "predicates": {},
                    },
                },
                "identifiers": [
                    {
                        "schema_id": S_ID,
                        "cred_def_id": CD_ID,
                        "rev_reg_id": None,
                        "timestamp": None,
                    },
                    {
                        "schema_id": S_ID,
                        "cred_def_id": CD_ID,
                        "rev_reg_id": None,
                        "timestamp": None,
                    },
                ],
            },
        )
        self.context.message = async_mock.MagicMock()

        with async_mock.patch.object(
            V10PresentationExchange, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            V10PresentationExchange, "retrieve_by_tag_filter", autospec=True
        ) as retrieve_ex:
            retrieve_ex.return_value = exchange_dummy
            exchange_out = await self.manager.receive_presentation()
            retrieve_ex.assert_called_once_with(
                self.context,
                {"thread_id": self.context.message._thread_id},
                {"connection_id": self.context.connection_record.connection_id},
            )
            save_ex.assert_called_once()

            assert exchange_out.state == (
                V10PresentationExchange.STATE_PRESENTATION_RECEIVED
            )

    async def test_receive_presentation_bait_and_switch(self):
        self.context.connection_record = async_mock.MagicMock()
        self.context.connection_record.connection_id = CONN_ID

        exchange_dummy = V10PresentationExchange(
            presentation_proposal_dict={
                "presentation_proposal": {
                    "@type": DIDCommPrefix.qualify_current(
                        "present-proof/1.0/presentation-preview"
                    ),
                    "attributes": [
                        {
                            "name": "favourite",
                            "cred_def_id": CD_ID,
                            "value": "no potato",
                        },
                        {"name": "icon", "cred_def_id": CD_ID, "value": "cG90YXRv"},
                    ],
                    "predicates": [],
                }
            },
            presentation_request={
                "name": "proof-request",
                "version": "1.0",
                "nonce": "1234567890",
                "requested_attributes": {
                    "0_favourite_uuid": {
                        "name": "favourite",
                        "restrictions": [{"cred_def_id": CD_ID}],
                    },
                    "1_icon_uuid": {
                        "name": "icon",
                        "restrictions": [{"cred_def_id": CD_ID}],
                    },
                },
            },
        )
        self.context.message = async_mock.MagicMock()
        self.context.message.indy_proof = async_mock.MagicMock(
            return_value={
                "proof": {"proofs": []},
                "requested_proof": {
                    "revealed_attrs": {
                        "0_favourite_uuid": {
                            "sub_proof_index": 0,
                            "raw": "potato",
                            "encoded": "12345678901234567890",
                        },
                        "1_icon_uuid": {
                            "sub_proof_index": 1,
                            "raw": "cG90YXRv",
                            "encoded": "23456789012345678901",
                        },
                    },
                    "self_attested_attrs": {},
                    "unrevealed_attrs": {},
                    "predicates": {},
                },
                "identifiers": [
                    {
                        "schema_id": S_ID,
                        "cred_def_id": CD_ID,
                        "rev_reg_id": None,
                        "timestamp": None,
                    },
                    {
                        "schema_id": S_ID,
                        "cred_def_id": CD_ID,
                        "rev_reg_id": None,
                        "timestamp": None,
                    },
                ],
            }
        )

        with async_mock.patch.object(
            V10PresentationExchange, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            V10PresentationExchange, "retrieve_by_tag_filter", autospec=True
        ) as retrieve_ex:
            retrieve_ex.return_value = exchange_dummy
            with self.assertRaises(PresentationManagerError):
                await self.manager.receive_presentation()

    async def test_receive_presentation_connection_less(self):
        exchange_dummy = V10PresentationExchange()
        self.context.message = async_mock.MagicMock()

        with async_mock.patch.object(
            V10PresentationExchange, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            V10PresentationExchange, "retrieve_by_tag_filter", autospec=True
        ) as retrieve_ex:
            retrieve_ex.return_value = exchange_dummy
            exchange_out = await self.manager.receive_presentation()
            retrieve_ex.assert_called_once_with(
                self.context, {"thread_id": self.context.message._thread_id}, None
            )
            save_ex.assert_called_once()

            assert exchange_out.state == (
                V10PresentationExchange.STATE_PRESENTATION_RECEIVED
            )

    async def test_verify_presentation(self):
        exchange_in = V10PresentationExchange()
        exchange_in.presentation = {
            "identifiers": [{"schema_id": S_ID, "cred_def_id": CD_ID}]
        }

        with async_mock.patch.object(
            V10PresentationExchange, "save", autospec=True
        ) as save_ex:
            exchange_out = await self.manager.verify_presentation(exchange_in)
            save_ex.assert_called_once()

            assert exchange_out.state == (V10PresentationExchange.STATE_VERIFIED)

    async def test_verify_presentation_with_revocation(self):
        exchange_in = V10PresentationExchange()
        exchange_in.presentation = {
            "identifiers": [
                {
                    "schema_id": S_ID,
                    "cred_def_id": CD_ID,
                    "rev_reg_id": RR_ID,
                    "timestamp": NOW,
                },
                {  # cover multiple instances of same rev reg
                    "schema_id": S_ID,
                    "cred_def_id": CD_ID,
                    "rev_reg_id": RR_ID,
                    "timestamp": NOW,
                },
            ]
        }

        with async_mock.patch.object(
            V10PresentationExchange, "save", autospec=True
        ) as save_ex:
            exchange_out = await self.manager.verify_presentation(exchange_in)
            save_ex.assert_called_once()

            assert exchange_out.state == (V10PresentationExchange.STATE_VERIFIED)

    async def test_send_presentation_ack(self):
        exchange = V10PresentationExchange()
        proposal = PresentationProposal()
        self.context.message = proposal

        responder = MockResponder()
        self.context.injector.bind_instance(BaseResponder, responder)

        await self.manager.send_presentation_ack(exchange)
        messages = responder.messages
        assert len(messages) == 1

    async def test_send_presentation_ack_no_responder(self):
        exchange = V10PresentationExchange()
        proposal = PresentationProposal()
        self.context.message = proposal

        self.context.injector.clear_binding(BaseResponder)
        await self.manager.send_presentation_ack(exchange)

    async def test_receive_presentation_ack(self):
        self.context.connection_record = async_mock.MagicMock()
        self.context.connection_record.connection_id = CONN_ID

        exchange_dummy = V10PresentationExchange()
        self.context.message = async_mock.MagicMock()

        with async_mock.patch.object(
            V10PresentationExchange, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            V10PresentationExchange, "retrieve_by_tag_filter", autospec=True
        ) as retrieve_ex:
            retrieve_ex.return_value = exchange_dummy
            exchange_out = await self.manager.receive_presentation_ack()
            save_ex.assert_called_once()

            assert exchange_out.state == (
                V10PresentationExchange.STATE_PRESENTATION_ACKED
            )
