import json

from time import time

from asynctest import mock as async_mock, TestCase as AsyncTestCase

from aries_cloudagent.protocols.issue_credential.v1_0.models.credential_exchange import (
    V10CredentialExchange,
)

from .....core.in_memory import InMemoryProfile
from .....indy.holder import IndyHolder, IndyHolderError
from .....indy.issuer import IndyIssuer
from .....indy.sdk.holder import IndySdkHolder
from .....indy.models.xform import indy_proof_req_preview2indy_requested_creds
from .....indy.models.pres_preview import (
    IndyPresAttrSpec,
    IndyPresPreview,
    IndyPresPredSpec,
)
from .....indy.sdk.verifier import IndySdkVerifier
from .....indy.verifier import IndyVerifier
from .....ledger.base import BaseLedger
from .....ledger.multiple_ledger.ledger_requests_executor import (
    IndyLedgerRequestsExecutor,
)
from .....messaging.decorators.attach_decorator import AttachDecorator
from .....messaging.request_context import RequestContext
from .....messaging.responder import BaseResponder, MockResponder
from .....storage.error import StorageNotFoundError

from ....didcomm_prefix import DIDCommPrefix

from ...indy import pres_exch_handler as test_indy_util_module

from .. import manager as test_module
from ..manager import PresentationManager, PresentationManagerError
from ..message_types import ATTACH_DECO_IDS, PRESENTATION, PRESENTATION_REQUEST
from ..messages.presentation import Presentation
from ..messages.presentation_ack import PresentationAck
from ..messages.presentation_problem_report import PresentationProblemReport
from ..messages.presentation_proposal import PresentationProposal
from ..messages.presentation_request import PresentationRequest
from ..models.presentation_exchange import V10PresentationExchange


NOW = int(time())
CONN_ID = "connection_id"
ISSUER_DID = "NcYxiDXkpYi6ov5FcYDi1e"
S_ID = f"{ISSUER_DID}:2:vidya:1.0"
CD_ID = f"{ISSUER_DID}:3:CL:{S_ID}:tag1"
RR_ID = f"{ISSUER_DID}:4:{CD_ID}:CL_ACCUM:0"
PRES_PREVIEW = IndyPresPreview(
    attributes=[
        IndyPresAttrSpec(name="player", cred_def_id=CD_ID, value="Richie Knucklez"),
        IndyPresAttrSpec(
            name="screenCapture",
            cred_def_id=CD_ID,
            mime_type="image/png",
            value="aW1hZ2luZSBhIHNjcmVlbiBjYXB0dXJl",
        ),
    ],
    predicates=[
        IndyPresPredSpec(
            name="highScore", cred_def_id=CD_ID, predicate=">=", threshold=1000000
        )
    ],
)
PRES_PREVIEW_NAMES = IndyPresPreview(
    attributes=[
        IndyPresAttrSpec(
            name="player", cred_def_id=CD_ID, value="Richie Knucklez", referent="0"
        ),
        IndyPresAttrSpec(
            name="screenCapture",
            cred_def_id=CD_ID,
            mime_type="image/png",
            value="aW1hZ2luZSBhIHNjcmVlbiBjYXB0dXJl",
            referent="0",
        ),
    ],
    predicates=[
        IndyPresPredSpec(
            name="highScore", cred_def_id=CD_ID, predicate=">=", threshold=1000000
        )
    ],
)
PROOF_REQ_NAME = "name"
PROOF_REQ_VERSION = "1.0"
PROOF_REQ_NONCE = "12345"
INDY_PROOF = {
    "proof": {
        "proofs": [
            {
                "primary_proof": {
                    "eq_proof": {
                        "revealed_attrs": {
                            "player": "51643998292319337989",
                            "screencapture": "124831723185628395682368329568235681",
                        },
                        "a_prime": "98381845469564775640588",
                        "e": "2889201651469315129053056279820725958192110265136",
                        "v": "337782521199137176224",
                        "m": {
                            "master_secret": "88675074759262558623",
                            "date": "3707627155679953691027082306",
                            "highscore": "251972383037120760793174059437326",
                        },
                        "m2": "2892781443118611948331343540849982215419978654911341",
                    },
                    "ge_proofs": [
                        {
                            "u": {
                                "0": "99189584890680947709857922351898933228959",
                                "3": "974568160016086782335901983921278203",
                                "2": "127290395299",
                                "1": "7521808223922",
                            },
                            "r": {
                                "3": "247458",
                                "2": "263046",
                                "1": "285214",
                                "DELTA": "4007402",
                                "0": "12066738",
                            },
                            "mj": "1507606",
                            "alpha": "20251550018805200",
                            "t": {
                                "1": "1262519732727",
                                "3": "82102416",
                                "0": "100578099981822",
                                "2": "47291",
                                "DELTA": "556736142765",
                            },
                            "predicate": {
                                "attr_name": "highscore",
                                "p_type": "GE",
                                "value": 1000000,
                            },
                        }
                    ],
                },
                "non_revoc_proof": {
                    "x_list": {
                        "rho": "128121489ACD4D778ECE",
                        "r": "1890DEFBB8A254",
                        "r_prime": "0A0861FFE96C",
                        "r_prime_prime": "058376CE",
                        "r_prime_prime_prime": "188DF30745A595",
                        "o": "0D0F7FA1",
                        "o_prime": "28165",
                        "m": "0187A9817897FC",
                        "m_prime": "91261D96B",
                        "t": "10FE96",
                        "t_prime": "10856A",
                        "m2": "B136089AAF",
                        "s": "018969A6D",
                        "c": "09186B6A",
                    },
                    "c_list": {
                        "e": "6 1B161",
                        "d": "6 19E861869",
                        "a": "6 541441EE2",
                        "g": "6 7601B068C",
                        "w": "21 10DE6 4 AAAA 5 2458 6 16161",
                        "s": "21 09616 4 1986 5 9797 6 BBBBB",
                        "u": "21 3213123 4 0616FFE 5 323 6 110861861",
                    },
                },
            }
        ],
        "aggregated_proof": {
            "c_hash": "81147637626525127013830996",
            "c_list": [
                [3, 18, 46, 12],
                [3, 136, 2, 39],
                [100, 111, 148, 193],
                [1, 123, 11, 152],
                [2, 138, 162, 227],
                [1, 239, 33, 47],
            ],
        },
    },
    "requested_proof": {
        "revealed_attrs": {
            "0_player_uuid": {
                "sub_proof_index": 0,
                "raw": "Richie Knucklez",
                "encoded": "516439982",
            },
            "0_screencapture_uuid": {
                "sub_proof_index": 0,
                "raw": "aW1hZ2luZSBhIHNjcmVlbiBjYXB0dXJl",
                "encoded": "4434954949",
            },
        },
        "self_attested_attrs": {},
        "unrevealed_attrs": {},
        "predicates": {"0_highscore_GE_uuid": {"sub_proof_index": 0}},
    },
    "identifiers": [
        {
            "schema_id": S_ID,
            "cred_def_id": CD_ID,
            "rev_reg_id": RR_ID,
            "timestamp": NOW,
        }
    ],
}
PRES = Presentation(
    comment="Test",
    presentations_attach=[
        AttachDecorator.data_base64(
            mapping=INDY_PROOF,
            ident=ATTACH_DECO_IDS[PRESENTATION],
        )
    ],
)
PRES.assign_thread_id("dummy")


class TestPresentationManager(AsyncTestCase):
    async def setUp(self):
        self.profile = InMemoryProfile.test_profile()
        injector = self.profile.context.injector

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
        injector.bind_instance(BaseLedger, self.ledger)
        injector.bind_instance(
            IndyLedgerRequestsExecutor,
            async_mock.MagicMock(
                get_ledger_for_identifier=async_mock.CoroutineMock(
                    return_value=(None, self.ledger)
                )
            ),
        )
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
        injector.bind_instance(IndyHolder, self.holder)

        Verifier = async_mock.MagicMock(IndyVerifier, autospec=True)
        self.verifier = Verifier()
        self.verifier.verify_presentation = async_mock.CoroutineMock(
            return_value=("true", [])
        )
        injector.bind_instance(IndyVerifier, self.verifier)

        self.manager = PresentationManager(self.profile)

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
        proposal = PresentationProposal()

        with async_mock.patch.object(
            V10PresentationExchange, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            PresentationProposal, "serialize", autospec=True
        ):
            exchange = await self.manager.create_exchange_for_proposal(
                CONN_ID,
                proposal,
                auto_present=None,
                auto_remove=True,
            )
            save_ex.assert_called_once()

            assert exchange.thread_id == proposal._thread_id
            assert exchange.initiator == V10PresentationExchange.INITIATOR_SELF
            assert exchange.role == V10PresentationExchange.ROLE_PROVER
            assert exchange.state == V10PresentationExchange.STATE_PROPOSAL_SENT
            assert exchange.auto_remove == True

    async def test_receive_proposal(self):
        connection_record = async_mock.MagicMock(connection_id=CONN_ID)
        proposal = PresentationProposal()

        with async_mock.patch.object(
            V10PresentationExchange, "save", autospec=True
        ) as save_ex:
            exchange = await self.manager.receive_proposal(proposal, connection_record)
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
        indy_proof_req = await PRES_PREVIEW.indy_proof_request(
            name=PROOF_REQ_NAME,
            version=PROOF_REQ_VERSION,
            nonce=PROOF_REQ_NONCE,
            profile=self.profile,
        )
        pres_req = PresentationRequest(
            request_presentations_attach=[
                AttachDecorator.data_base64(
                    mapping=indy_proof_req,
                    ident=ATTACH_DECO_IDS[PRESENTATION_REQUEST],
                )
            ]
        )

        with async_mock.patch.object(
            V10PresentationExchange, "save", autospec=True
        ) as save_ex:
            exchange = await self.manager.create_exchange_for_request(
                CONN_ID,
                pres_req,
                auto_remove=True,
            )
            save_ex.assert_called_once()

            assert exchange.thread_id == pres_req._thread_id
            assert exchange.initiator == V10PresentationExchange.INITIATOR_SELF
            assert exchange.role == V10PresentationExchange.ROLE_VERIFIER
            assert exchange.state == V10PresentationExchange.STATE_REQUEST_SENT
            assert exchange.auto_remove == True

    async def test_receive_request(self):
        exchange_in = V10PresentationExchange()

        with async_mock.patch.object(
            V10PresentationExchange, "save", autospec=True
        ) as save_ex:
            exchange_out = await self.manager.receive_request(exchange_in)
            save_ex.assert_called_once()

            assert exchange_out.state == V10PresentationExchange.STATE_REQUEST_RECEIVED

    async def test_create_presentation(self):
        exchange_in = V10PresentationExchange()
        indy_proof_req = await PRES_PREVIEW.indy_proof_request(
            name=PROOF_REQ_NAME,
            version=PROOF_REQ_VERSION,
            nonce=PROOF_REQ_NONCE,
            profile=self.profile,
        )

        exchange_in.presentation_request = indy_proof_req

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
            test_indy_util_module, "RevocationRegistry", autospec=True
        ) as mock_rr:
            mock_rr.from_definition = async_mock.MagicMock(return_value=more_magic_rr)

            mock_attach_decorator.data_base64 = async_mock.MagicMock(
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
        exchange_in = V10PresentationExchange()
        indy_proof_req = await PRES_PREVIEW.indy_proof_request(
            name=PROOF_REQ_NAME,
            version=PROOF_REQ_VERSION,
            nonce=PROOF_REQ_NONCE,
            profile=self.profile,
        )
        indy_proof_req["non_revoked"] = None  # simulate interop with indy-vcx

        exchange_in.presentation_request = indy_proof_req

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
            test_indy_util_module, "RevocationRegistry", autospec=True
        ) as mock_rr:
            mock_rr.from_definition = async_mock.MagicMock(return_value=more_magic_rr)

            mock_attach_decorator.data_base64 = async_mock.MagicMock(
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
        PRES_PREVIEW_SELFIE = IndyPresPreview(
            attributes=[
                IndyPresAttrSpec(name="player", value="Richie Knucklez"),
                IndyPresAttrSpec(
                    name="screenCapture",
                    mime_type="image/png",
                    value="aW1hZ2luZSBhIHNjcmVlbiBjYXB0dXJl",
                ),
            ],
            predicates=[
                IndyPresPredSpec(
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
            profile=self.profile,
        )

        exchange_in.presentation_request = indy_proof_req

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
            test_indy_util_module, "RevocationRegistry", autospec=True
        ) as mock_rr:
            mock_rr.from_definition = async_mock.MagicMock(return_value=more_magic_rr)

            mock_attach_decorator.data_base64 = async_mock.MagicMock(
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
        Ledger = async_mock.MagicMock(BaseLedger, autospec=True)
        self.ledger = Ledger()
        self.ledger.get_schema = async_mock.CoroutineMock(
            return_value=async_mock.MagicMock()
        )
        self.ledger.get_credential_definition = async_mock.CoroutineMock(
            return_value={"value": {"revocation": None}}
        )
        self.profile.context.injector.bind_instance(BaseLedger, self.ledger)

        exchange_in = V10PresentationExchange()
        indy_proof_req = await PRES_PREVIEW.indy_proof_request(
            name=PROOF_REQ_NAME,
            version=PROOF_REQ_VERSION,
            nonce=PROOF_REQ_NONCE,
            profile=self.profile,
        )

        exchange_in.presentation_request = indy_proof_req

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
        self.profile.context.injector.bind_instance(IndyHolder, self.holder)

        with async_mock.patch.object(
            V10PresentationExchange, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            test_module, "AttachDecorator", autospec=True
        ) as mock_attach_decorator, async_mock.patch.object(
            test_indy_util_module.LOGGER, "info", async_mock.MagicMock()
        ) as mock_log_info:
            mock_attach_decorator.data_base64 = async_mock.MagicMock(
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

            # exercise superfluous timestamp removal
            for pred_reft_spec in req_creds["requested_predicates"].values():
                pred_reft_spec["timestamp"] = 1234567890
            await self.manager.create_presentation(exchange_in, req_creds)
            mock_log_info.assert_called_once()

    async def test_create_presentation_bad_revoc_state(self):
        exchange_in = V10PresentationExchange()
        indy_proof_req = await PRES_PREVIEW.indy_proof_request(
            name=PROOF_REQ_NAME,
            version=PROOF_REQ_VERSION,
            nonce=PROOF_REQ_NONCE,
            profile=self.profile,
        )

        exchange_in.presentation_request = indy_proof_req

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
            side_effect=IndyHolderError("Problem", {"message": "Nope"})
        )
        self.profile.context.injector.bind_instance(IndyHolder, self.holder)

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
            test_indy_util_module, "RevocationRegistry", autospec=True
        ) as mock_rr:
            mock_rr.from_definition = async_mock.MagicMock(return_value=more_magic_rr)

            mock_attach_decorator.data_base64 = async_mock.MagicMock(
                return_value=mock_attach_decorator
            )

            req_creds = await indy_proof_req_preview2indy_requested_creds(
                indy_proof_req, holder=self.holder
            )

            with self.assertRaises(IndyHolderError):
                await self.manager.create_presentation(exchange_in, req_creds)

    async def test_create_presentation_multi_matching_proposal_creds_names(self):
        exchange_in = V10PresentationExchange()
        indy_proof_req = await PRES_PREVIEW_NAMES.indy_proof_request(
            name=PROOF_REQ_NAME,
            version=PROOF_REQ_VERSION,
            nonce=PROOF_REQ_NONCE,
            profile=self.profile,
        )

        exchange_in.presentation_request = indy_proof_req

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
        self.profile.context.injector.bind_instance(IndyHolder, self.holder)

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
            test_indy_util_module, "RevocationRegistry", autospec=True
        ) as mock_rr:
            mock_rr.from_definition = async_mock.MagicMock(return_value=more_magic_rr)

            mock_attach_decorator.data_base64 = async_mock.MagicMock(
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
            profile=self.profile,
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
        connection_record = async_mock.MagicMock(connection_id=CONN_ID)

        exchange_dummy = V10PresentationExchange(
            presentation_proposal_dict={
                "presentation_proposal": {
                    "@type": DIDCommPrefix.qualify_current(
                        "present-proof/1.0/presentation-preview"
                    ),
                    "attributes": [
                        {
                            "name": "player",
                            "cred_def_id": CD_ID,
                            "value": "Richie Knucklez",
                        },
                        {
                            "name": "screenCapture",
                            "cred_def_id": CD_ID,
                            "value": "aW1hZ2luZSBhIHNjcmVlbiBjYXB0dXJl",
                        },
                    ],
                    "predicates": [
                        {
                            "name": "highScore",
                            "cred_def_id": CD_ID,
                            "predicate": ">=",
                            "threshold": 1000000,
                        }
                    ],
                }
            },
            presentation_request={
                "name": "proof-request",
                "version": "1.0",
                "nonce": "1234567890",
                "requested_attributes": {
                    "0_player_uuid": {
                        "name": "player",
                        "restrictions": [{"cred_def_id": CD_ID}],
                    },
                    "0_screencapture_uuid": {
                        "name": "screenCapture",
                        "restrictions": [{"cred_def_id": CD_ID}],
                    },
                },
                "requested_predicates": {
                    "0_highscore_GE_uuid": {
                        "name": "highScore",
                        "p_type": ">=",
                        "p_value": 1000000,
                        "restrictions": [{"cred_def_id": CD_ID}],
                    }
                },
            },
            presentation={
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
                            "raw": "aW1hZ2luZSBhIHNjcmVlbiBjYXB0dXJl",
                            "encoded": "12345678901234567890",
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
            },
        )

        with async_mock.patch.object(
            V10PresentationExchange, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            V10PresentationExchange, "retrieve_by_tag_filter", autospec=True
        ) as retrieve_ex, async_mock.patch.object(
            self.profile,
            "session",
            async_mock.MagicMock(return_value=self.profile.session()),
        ) as session:
            retrieve_ex.side_effect = [exchange_dummy]
            exchange_out = await self.manager.receive_presentation(
                PRES, connection_record, None
            )
            retrieve_ex.assert_called_once_with(
                session.return_value,
                {"thread_id": "dummy"},
                {
                    "role": V10PresentationExchange.ROLE_VERIFIER,
                    "connection_id": CONN_ID,
                },
            )
            save_ex.assert_called_once()
            assert exchange_out.state == (
                V10PresentationExchange.STATE_PRESENTATION_RECEIVED
            )

    async def test_receive_presentation_oob(self):
        exchange_dummy = V10PresentationExchange(
            presentation_proposal_dict={
                "presentation_proposal": {
                    "@type": DIDCommPrefix.qualify_current(
                        "present-proof/1.0/presentation-preview"
                    ),
                    "attributes": [
                        {
                            "name": "player",
                            "cred_def_id": CD_ID,
                            "value": "Richie Knucklez",
                        },
                        {
                            "name": "screenCapture",
                            "cred_def_id": CD_ID,
                            "value": "aW1hZ2luZSBhIHNjcmVlbiBjYXB0dXJl",
                        },
                    ],
                    "predicates": [
                        {
                            "name": "highScore",
                            "cred_def_id": CD_ID,
                            "predicate": ">=",
                            "threshold": 1000000,
                        }
                    ],
                }
            },
            presentation_request={
                "name": "proof-request",
                "version": "1.0",
                "nonce": "1234567890",
                "requested_attributes": {
                    "0_player_uuid": {
                        "name": "player",
                        "restrictions": [{"cred_def_id": CD_ID}],
                    },
                    "0_screencapture_uuid": {
                        "name": "screenCapture",
                        "restrictions": [{"cred_def_id": CD_ID}],
                    },
                },
                "requested_predicates": {
                    "0_highscore_GE_uuid": {
                        "name": "highScore",
                        "p_type": ">=",
                        "p_value": 1000000,
                        "restrictions": [{"cred_def_id": CD_ID}],
                    }
                },
            },
            presentation={
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
                            "raw": "aW1hZ2luZSBhIHNjcmVlbiBjYXB0dXJl",
                            "encoded": "12345678901234567890",
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
            },
        )

        with async_mock.patch.object(
            V10PresentationExchange, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            V10PresentationExchange, "retrieve_by_tag_filter", autospec=True
        ) as retrieve_ex, async_mock.patch.object(
            self.profile,
            "session",
            async_mock.MagicMock(return_value=self.profile.session()),
        ) as session:
            retrieve_ex.side_effect = [exchange_dummy]
            exchange_out = await self.manager.receive_presentation(PRES, None, None)
            retrieve_ex.assert_called_once_with(
                session.return_value,
                {"thread_id": "dummy"},
                {"role": V10PresentationExchange.ROLE_VERIFIER, "connection_id": None},
            )
            assert exchange_out.state == (
                V10PresentationExchange.STATE_PRESENTATION_RECEIVED
            )

    async def test_receive_presentation_bait_and_switch(self):
        connection_record = async_mock.MagicMock(connection_id=CONN_ID)

        exchange_dummy = V10PresentationExchange(
            presentation_proposal_dict={
                "presentation_proposal": {
                    "@type": DIDCommPrefix.qualify_current(
                        "present-proof/1.0/presentation-preview"
                    ),
                    "attributes": [
                        {
                            "name": "player",
                            "cred_def_id": CD_ID,
                            "value": "Richie Knucklez",
                        },
                        {
                            "name": "screenCapture",
                            "cred_def_id": CD_ID,
                            "value": "YSBwaWN0dXJlIG9mIGEgcG90YXRv",
                        },
                    ],
                    "predicates": [
                        {
                            "name": "highScore",
                            "cred_def_id": CD_ID,
                            "predicate": ">=",
                            "threshold": 1000000,
                        }
                    ],
                }
            },
            presentation_request={
                "name": "proof-request",
                "version": "1.0",
                "nonce": "1234567890",
                "requested_attributes": {
                    "0_player_uuid": {
                        "name": "player",
                        "restrictions": [{"cred_def_id": CD_ID}],
                    },
                    "0_screencapture_uuid": {
                        "name": "screenCapture",
                        "restrictions": [{"cred_def_id": CD_ID}],
                    },
                },
                "requested_predicates": {
                    "0_highscore_GE_uuid": {
                        "name": "highScore",
                        "p_type": ">=",
                        "p_value": 1000000,
                        "restrictions": [{"cred_def_id": CD_ID}],
                    }
                },
            },
            presentation={
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
                            "raw": "aW1hZ2luZSBhIHNjcmVlbiBjYXB0dXJl",
                            "encoded": "12345678901234567890",
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
            },
        )

        with async_mock.patch.object(
            V10PresentationExchange, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            V10PresentationExchange, "retrieve_by_tag_filter", autospec=True
        ) as retrieve_ex:
            retrieve_ex.return_value = exchange_dummy
            with self.assertRaises(PresentationManagerError):
                await self.manager.receive_presentation(PRES, connection_record, None)

    async def test_receive_presentation_connectionless(self):
        exchange_dummy = V10PresentationExchange()

        with async_mock.patch.object(
            V10PresentationExchange, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            V10PresentationExchange, "retrieve_by_tag_filter", autospec=True
        ) as retrieve_ex, async_mock.patch.object(
            self.profile,
            "session",
            async_mock.MagicMock(return_value=self.profile.session()),
        ) as session:
            retrieve_ex.return_value = exchange_dummy
            exchange_out = await self.manager.receive_presentation(PRES, None, None)
            retrieve_ex.assert_called_once_with(
                session.return_value,
                {"thread_id": PRES._thread_id},
                {"role": V10PresentationExchange.ROLE_VERIFIER, "connection_id": None},
            )
            save_ex.assert_called_once()

            assert exchange_out.state == (
                V10PresentationExchange.STATE_PRESENTATION_RECEIVED
            )

    async def test_verify_presentation(self):
        indy_proof_req = await PRES_PREVIEW.indy_proof_request(
            name=PROOF_REQ_NAME,
            version=PROOF_REQ_VERSION,
            nonce=PROOF_REQ_NONCE,
            profile=self.profile,
        )
        pres_req = PresentationRequest(
            request_presentations_attach=[
                AttachDecorator.data_base64(
                    mapping=indy_proof_req,
                    ident=ATTACH_DECO_IDS[PRESENTATION_REQUEST],
                )
            ]
        )
        exchange_in = V10PresentationExchange(
            presentation_exchange_id="dummy-pxid",
            connection_id="dummy-conn-id",
            initiator=V10PresentationExchange.INITIATOR_SELF,
            role=V10PresentationExchange.ROLE_VERIFIER,
            presentation_request=pres_req,
            presentation=INDY_PROOF,
        )

        with async_mock.patch.object(
            V10PresentationExchange, "save", autospec=True
        ) as save_ex:
            exchange_out = await self.manager.verify_presentation(exchange_in)
            save_ex.assert_called_once()

            assert exchange_out.state == (V10PresentationExchange.STATE_VERIFIED)

    """
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
    """

    async def test_send_presentation_ack(self):
        exchange = V10PresentationExchange(connection_id="dummy")

        responder = MockResponder()
        self.profile.context.injector.bind_instance(BaseResponder, responder)

        await self.manager.send_presentation_ack(exchange)
        messages = responder.messages
        assert len(messages) == 1

    async def test_send_presentation_ack_oob(self):
        exchange = V10PresentationExchange(thread_id="some-thread-id")

        responder = MockResponder()
        self.profile.context.injector.bind_instance(BaseResponder, responder)

        with async_mock.patch.object(
            test_module.OobRecord, "retrieve_by_tag_filter"
        ) as mock_retrieve_oob, async_mock.patch.object(
            self.profile,
            "session",
            async_mock.MagicMock(return_value=self.profile.session()),
        ) as session:
            await self.manager.send_presentation_ack(exchange)
            messages = responder.messages
            mock_retrieve_oob.assert_called_once_with(
                session.return_value, {"attach_thread_id": "some-thread-id"}
            )
            assert len(messages) == 1

    async def test_send_presentation_ack_no_responder(self):
        exchange = V10PresentationExchange()

        self.profile.context.injector.clear_binding(BaseResponder)
        await self.manager.send_presentation_ack(exchange)

    async def test_receive_presentation_ack_a(self):
        connection_record = async_mock.MagicMock(connection_id=CONN_ID)

        exchange_dummy = V10PresentationExchange()
        message = async_mock.MagicMock()

        with async_mock.patch.object(
            V10PresentationExchange, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            V10PresentationExchange, "retrieve_by_tag_filter", autospec=True
        ) as retrieve_ex:
            retrieve_ex.return_value = exchange_dummy
            exchange_out = await self.manager.receive_presentation_ack(
                message, connection_record
            )
            save_ex.assert_called_once()

            assert exchange_out.state == (
                V10PresentationExchange.STATE_PRESENTATION_ACKED
            )

    async def test_receive_presentation_ack_b(self):
        connection_record = async_mock.MagicMock(connection_id=CONN_ID)

        exchange_dummy = V10PresentationExchange()
        message = async_mock.MagicMock(_verification_result="true")

        with async_mock.patch.object(
            V10PresentationExchange, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            V10PresentationExchange, "retrieve_by_tag_filter", autospec=True
        ) as retrieve_ex:
            retrieve_ex.return_value = exchange_dummy
            exchange_out = await self.manager.receive_presentation_ack(
                message, connection_record
            )
            save_ex.assert_called_once()

            assert exchange_out.state == (
                V10PresentationExchange.STATE_PRESENTATION_ACKED
            )
            assert exchange_out.verified == "true"

    async def test_receive_problem_report(self):
        connection_id = "connection-id"
        stored_exchange = V10PresentationExchange(
            presentation_exchange_id="dummy-pxid",
            connection_id=connection_id,
            initiator=V10PresentationExchange.INITIATOR_SELF,
            role=V10PresentationExchange.ROLE_VERIFIER,
            state=V10PresentationExchange.STATE_PROPOSAL_RECEIVED,
            thread_id="dummy-thid",
        )
        problem = PresentationProblemReport(
            description={
                "code": test_module.ProblemReportReason.ABANDONED.value,
                "en": "Change of plans",
            }
        )

        with async_mock.patch.object(
            V10PresentationExchange, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            V10PresentationExchange,
            "retrieve_by_tag_filter",
            async_mock.CoroutineMock(),
        ) as retrieve_ex, async_mock.patch.object(
            self.profile,
            "session",
            async_mock.MagicMock(return_value=self.profile.session()),
        ) as session:
            retrieve_ex.return_value = stored_exchange

            ret_exchange = await self.manager.receive_problem_report(
                problem, connection_id
            )
            retrieve_ex.assert_called_once_with(
                session.return_value,
                {"thread_id": problem._thread_id},
                {"connection_id": connection_id},
            )
            save_ex.assert_called_once()

            assert ret_exchange.state == V10CredentialExchange.STATE_ABANDONED

    async def test_receive_problem_report_x(self):
        connection_id = "connection-id"
        stored_exchange = V10PresentationExchange(
            presentation_exchange_id="dummy-pxid",
            connection_id=connection_id,
            initiator=V10PresentationExchange.INITIATOR_SELF,
            role=V10PresentationExchange.ROLE_VERIFIER,
            state=V10PresentationExchange.STATE_PROPOSAL_RECEIVED,
            thread_id="dummy-thid",
        )
        problem = PresentationProblemReport(
            description={
                "code": test_module.ProblemReportReason.ABANDONED.value,
                "en": "Change of plans",
            }
        )

        with async_mock.patch.object(
            V10PresentationExchange,
            "retrieve_by_tag_filter",
            async_mock.CoroutineMock(),
        ) as retrieve_ex:
            retrieve_ex.side_effect = test_module.StorageNotFoundError("No such record")

            with self.assertRaises(test_module.StorageNotFoundError):
                await self.manager.receive_problem_report(problem, connection_id)
