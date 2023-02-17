import json

from copy import deepcopy
from time import time

from asynctest import mock as async_mock, TestCase as AsyncTestCase

from .....core.in_memory import InMemoryProfile
from .....indy.holder import IndyHolder
from .....indy.models.xform import indy_proof_req_preview2indy_requested_creds
from .....indy.models.pres_preview import (
    IndyPresAttrSpec,
    IndyPresPreview,
    IndyPresPredSpec,
)
from .....indy.verifier import IndyVerifier
from .....ledger.base import BaseLedger
from .....ledger.multiple_ledger.ledger_requests_executor import (
    IndyLedgerRequestsExecutor,
)
from .....messaging.decorators.attach_decorator import AttachDecorator
from .....messaging.responder import BaseResponder, MockResponder
from .....multitenant.base import BaseMultitenantManager
from .....multitenant.manager import MultitenantManager
from .....storage.error import StorageNotFoundError

from ...indy import pres_exch_handler as test_indy_util_module

from .. import manager as test_module
from ..formats.handler import V20PresFormatHandlerError
from ..formats.dif.handler import DIFPresFormatHandler
from ..formats.dif.tests.test_handler import (
    DIF_PRES_REQUEST_B as DIF_PRES_REQ,
    DIF_PRES_REQUEST_A as DIF_PRES_REQ_ALT,
    DIF_PRES,
)
from ..formats.indy import handler as test_indy_handler
from ..manager import V20PresManager, V20PresManagerError
from ..message_types import (
    ATTACHMENT_FORMAT,
    PRES_20_PROPOSAL,
    PRES_20_REQUEST,
    PRES_20,
)
from ..messages.pres import V20Pres
from ..messages.pres_format import V20PresFormat
from ..messages.pres_problem_report import V20PresProblemReport
from ..messages.pres_proposal import V20PresProposal
from ..messages.pres_request import V20PresRequest
from ..models.pres_exchange import V20PresExRecord

from .....vc.vc_ld.validation_result import PresentationVerificationResult
from .....vc.tests.document_loader import custom_document_loader
from .....vc.ld_proofs import DocumentLoader

CONN_ID = "connection_id"
ISSUER_DID = "NcYxiDXkpYi6ov5FcYDi1e"
S_ID = f"{ISSUER_DID}:2:vidya:1.0"
CD_ID = f"{ISSUER_DID}:3:CL:{S_ID}:tag1"
RR_ID = f"{ISSUER_DID}:4:{CD_ID}:CL_ACCUM:0"
PROOF_REQ_NAME = "name"
PROOF_REQ_VERSION = "1.0"
PROOF_REQ_NONCE = "12345"

NOW = int(time())
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
INDY_PROOF_REQ_NAME = {
    "name": PROOF_REQ_NAME,
    "version": PROOF_REQ_VERSION,
    "nonce": PROOF_REQ_NONCE,
    "requested_attributes": {
        "0_player_uuid": {
            "name": "player",
            "restrictions": [{"cred_def_id": CD_ID}],
            "non_revoked": {"from": NOW, "to": NOW},
        },
        "0_screencapture_uuid": {
            "name": "screenCapture",
            "restrictions": [{"cred_def_id": CD_ID}],
            "non_revoked": {"from": NOW, "to": NOW},
        },
    },
    "requested_predicates": {
        "0_highscore_GE_uuid": {
            "name": "highScore",
            "p_type": ">=",
            "p_value": 1000000,
            "restrictions": [{"cred_def_id": CD_ID}],
            "non_revoked": {"from": NOW, "to": NOW},
        }
    },
}
INDY_PROOF_REQ_NAMES = {
    "name": PROOF_REQ_NAME,
    "version": PROOF_REQ_VERSION,
    "nonce": PROOF_REQ_NONCE,
    "requested_attributes": {
        "0_player_uuid": {
            "names": ["player", "screenCapture"],
            "restrictions": [{"cred_def_id": CD_ID}],
            "non_revoked": {"from": NOW, "to": NOW},
        }
    },
    "requested_predicates": {
        "0_highscore_GE_uuid": {
            "name": "highScore",
            "p_type": ">=",
            "p_value": 1000000,
            "restrictions": [{"cred_def_id": CD_ID}],
            "non_revoked": {"from": NOW, "to": NOW},
        }
    },
}
INDY_PROOF_REQ_SELFIE = {
    "name": PROOF_REQ_NAME,
    "version": PROOF_REQ_VERSION,
    "nonce": PROOF_REQ_NONCE,
    "requested_attributes": {
        "self_player_uuid": {"name": "player"},
        "self_screencapture_uuid": {"name": "screenCapture"},
    },
    "requested_predicates": {
        "0_highscore_GE_uuid": {"name": "highScore", "p_type": ">=", "p_value": 1000000}
    },
}
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
INDY_PROOF_NAMES = {
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
        "revealed_attrs": {},
        "revealed_attr_groups": {
            "0_player_uuid": {
                "sub_proof_index": 0,
                "values": {
                    "player": {
                        "raw": "Richie Knucklez",
                        "encoded": "516439982",
                    },
                    "screenCapture": {
                        "raw": "aW1hZ2luZSBhIHNjcmVlbiBjYXB0dXJl",
                        "encoded": "4434954949",
                    },
                },
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


class TestV20PresManager(AsyncTestCase):
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

        self.manager = V20PresManager(self.profile)

    async def test_record_eq(self):
        same = [
            V20PresExRecord(
                pres_ex_id="dummy-0",
                thread_id="thread-0",
                role=V20PresExRecord.ROLE_PROVER,
            )
        ] * 2
        diff = [
            V20PresExRecord(
                pres_ex_id="dummy-1",
                role=V20PresExRecord.ROLE_PROVER,
            ),
            V20PresExRecord(
                pres_ex_id="dummy-0",
                thread_id="thread-1",
                role=V20PresExRecord.ROLE_PROVER,
            ),
            V20PresExRecord(
                pres_ex_id="dummy-1",
                thread_id="thread-0",
                role=V20PresExRecord.ROLE_VERIFIER,
            ),
        ]

        for i in range(len(same) - 1):
            for j in range(i, len(same)):
                assert same[i] == same[j]

        for i in range(len(diff) - 1):
            for j in range(i, len(diff)):
                assert diff[i] == diff[j] if i == j else diff[i] != diff[j]

    async def test_create_exchange_for_proposal(self):
        proposal = V20PresProposal(
            formats=[
                V20PresFormat(attach_id="indy", format_=V20PresFormat.Format.INDY.aries)
            ]
        )

        with async_mock.patch.object(
            V20PresExRecord, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            V20PresProposal, "serialize", autospec=True
        ):
            px_rec = await self.manager.create_exchange_for_proposal(
                CONN_ID, proposal, auto_present=None
            )
            save_ex.assert_called_once()

            assert px_rec.thread_id == proposal._thread_id
            assert px_rec.initiator == V20PresExRecord.INITIATOR_SELF
            assert px_rec.role == V20PresExRecord.ROLE_PROVER
            assert px_rec.state == V20PresExRecord.STATE_PROPOSAL_SENT

    async def test_receive_proposal(self):
        connection_record = async_mock.MagicMock(connection_id=CONN_ID)
        proposal = V20PresProposal(
            formats=[
                V20PresFormat(attach_id="indy", format_=V20PresFormat.Format.INDY.aries)
            ]
        )
        with async_mock.patch.object(V20PresExRecord, "save", autospec=True) as save_ex:
            px_rec = await self.manager.receive_pres_proposal(
                proposal,
                connection_record,
            )
            save_ex.assert_called_once()

            assert px_rec.state == V20PresExRecord.STATE_PROPOSAL_RECEIVED

    async def test_create_bound_request_a(self):
        comment = "comment"

        proposal = V20PresProposal(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[PRES_20_PROPOSAL][
                        V20PresFormat.Format.INDY.api
                    ],
                )
            ],
            proposals_attach=[
                AttachDecorator.data_base64(INDY_PROOF_REQ_NAME, ident="indy")
            ],
        )
        px_rec = V20PresExRecord(
            pres_proposal=proposal.serialize(),
            role=V20PresExRecord.ROLE_VERIFIER,
        )
        px_rec.save = async_mock.CoroutineMock()
        request_data = {
            "name": PROOF_REQ_NAME,
            "version": PROOF_REQ_VERSION,
            "nonce": PROOF_REQ_NONCE,
        }
        (ret_px_rec, pres_req_msg) = await self.manager.create_bound_request(
            pres_ex_record=px_rec,
            request_data=request_data,
            comment=comment,
        )
        assert ret_px_rec is px_rec
        px_rec.save.assert_called_once()

    async def test_create_bound_request_b(self):
        comment = "comment"

        proposal = V20PresProposal(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[PRES_20_PROPOSAL][
                        V20PresFormat.Format.INDY.api
                    ],
                )
            ],
            proposals_attach=[
                AttachDecorator.data_base64(INDY_PROOF_REQ_NAME, ident="indy")
            ],
        )
        px_rec = V20PresExRecord(
            pres_proposal=proposal.serialize(),
            role=V20PresExRecord.ROLE_VERIFIER,
        )
        px_rec.save = async_mock.CoroutineMock()
        (ret_px_rec, pres_req_msg) = await self.manager.create_bound_request(
            pres_ex_record=px_rec,
            comment=comment,
        )
        assert ret_px_rec is px_rec
        px_rec.save.assert_called_once()

    async def test_create_bound_request_no_format(self):
        px_rec = V20PresExRecord(
            pres_proposal=V20PresProposal(
                formats=[],
                proposals_attach=[],
            ).serialize(),
            role=V20PresExRecord.ROLE_VERIFIER,
        )
        with self.assertRaises(V20PresManagerError) as context:
            await self.manager.create_bound_request(
                pres_ex_record=px_rec,
                request_data={},
                comment="test",
            )
        assert "No supported formats" in str(context.exception)

    async def test_create_pres_no_format(self):
        px_rec = V20PresExRecord(
            pres_proposal=V20PresProposal(
                formats=[],
                proposals_attach=[],
            ).serialize(),
            pres_request=V20PresRequest(
                formats=[], request_presentations_attach=[]
            ).serialize(),
        )
        with self.assertRaises(V20PresManagerError) as context:
            await self.manager.create_pres(
                pres_ex_record=px_rec,
                request_data={},
                comment="test",
            )
        assert "No supported formats" in str(context.exception)

    async def test_create_pres_catch_diferror(self):
        px_rec = V20PresExRecord(
            pres_request=V20PresRequest(
                formats=[
                    V20PresFormat(
                        attach_id="dif",
                        format_=ATTACHMENT_FORMAT[PRES_20_REQUEST][
                            V20PresFormat.Format.DIF.api
                        ],
                    )
                ],
                request_presentations_attach=[
                    AttachDecorator.data_json(DIF_PRES_REQ, ident="dif")
                ],
            ).serialize(),
        )
        with async_mock.patch.object(
            DIFPresFormatHandler, "create_pres", autospec=True
        ) as mock_create_pres:
            mock_create_pres.return_value = None
            with self.assertRaises(V20PresManagerError) as context:
                await self.manager.create_pres(
                    pres_ex_record=px_rec,
                    request_data={},
                    comment="test",
                )
            assert "Unable to create presentation. ProblemReport message sent" in str(
                context.exception
            )

    async def test_receive_pres_catch_diferror(self):
        connection_record = async_mock.MagicMock(connection_id=CONN_ID)
        pres_x = V20Pres(
            formats=[
                V20PresFormat(
                    attach_id="dif",
                    format_=ATTACHMENT_FORMAT[PRES_20][V20PresFormat.Format.DIF.api],
                )
            ],
            presentations_attach=[
                AttachDecorator.data_json(
                    mapping=DIF_PRES,
                    ident="dif",
                )
            ],
        )
        pres_req = V20PresRequest(
            formats=[
                V20PresFormat(
                    attach_id="dif",
                    format_=ATTACHMENT_FORMAT[PRES_20_REQUEST][
                        V20PresFormat.Format.DIF.api
                    ],
                )
            ],
            request_presentations_attach=[
                AttachDecorator.data_json(DIF_PRES_REQ, ident="dif")
            ],
        )
        px_rec = V20PresExRecord(
            pres_request=pres_req.serialize(),
            pres=pres_x.serialize(),
        )
        with async_mock.patch.object(
            DIFPresFormatHandler, "receive_pres", autospec=True
        ) as mock_receive_pres, async_mock.patch.object(
            V20PresExRecord, "retrieve_by_tag_filter", autospec=True
        ) as retrieve_ex:
            mock_receive_pres.return_value = False
            retrieve_ex.side_effect = [px_rec]
            with self.assertRaises(V20PresManagerError) as context:
                await self.manager.receive_pres(pres_x, connection_record, None)
            assert "Unable to verify received presentation." in str(context.exception)

    async def test_create_exchange_for_request(self):
        pres_req = V20PresRequest(
            comment="Test",
            will_confirm=True,
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[PRES_20_REQUEST][
                        V20PresFormat.Format.INDY.api
                    ],
                )
            ],
            request_presentations_attach=[
                AttachDecorator.data_base64(mapping=INDY_PROOF_REQ_NAME, ident="indy")
            ],
        )
        pres_req.assign_thread_id("dummy")

        with async_mock.patch.object(V20PresExRecord, "save", autospec=True) as save_ex:
            px_rec = await self.manager.create_exchange_for_request(CONN_ID, pres_req)
            save_ex.assert_called_once()

            assert px_rec.thread_id == pres_req._thread_id
            assert px_rec.initiator == V20PresExRecord.INITIATOR_SELF
            assert px_rec.role == V20PresExRecord.ROLE_VERIFIER
            assert px_rec.state == V20PresExRecord.STATE_REQUEST_SENT

    async def test_receive_pres_request(self):
        px_rec_in = V20PresExRecord()

        with async_mock.patch.object(V20PresExRecord, "save", autospec=True) as save_ex:
            px_rec_out = await self.manager.receive_pres_request(px_rec_in)
            save_ex.assert_called_once()

            assert px_rec_out.state == V20PresExRecord.STATE_REQUEST_RECEIVED

    async def test_create_pres_indy(self):
        pres_request = V20PresRequest(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[PRES_20_REQUEST][
                        V20PresFormat.Format.INDY.api
                    ],
                )
            ],
            request_presentations_attach=[
                AttachDecorator.data_base64(INDY_PROOF_REQ_NAME, ident="indy")
            ],
        )
        px_rec_in = V20PresExRecord(pres_request=pres_request.serialize())
        more_magic_rr = async_mock.MagicMock(
            get_or_fetch_local_tails_path=async_mock.CoroutineMock(
                return_value="/tmp/sample/tails/path"
            )
        )
        with async_mock.patch.object(
            V20PresExRecord, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            test_indy_handler, "AttachDecorator", autospec=True
        ) as mock_attach_decorator, async_mock.patch.object(
            test_indy_util_module, "RevocationRegistry", autospec=True
        ) as mock_rr:
            mock_rr.from_definition = async_mock.MagicMock(return_value=more_magic_rr)

            mock_attach_decorator.data_base64 = async_mock.MagicMock(
                return_value=mock_attach_decorator
            )

            req_creds = await indy_proof_req_preview2indy_requested_creds(
                INDY_PROOF_REQ_NAME, preview=None, holder=self.holder
            )
            request_data = {"indy": req_creds}
            assert not req_creds["self_attested_attributes"]
            assert len(req_creds["requested_attributes"]) == 2
            assert len(req_creds["requested_predicates"]) == 1

            (px_rec_out, pres_msg) = await self.manager.create_pres(
                px_rec_in, request_data
            )
            save_ex.assert_called_once()
            assert px_rec_out.state == V20PresExRecord.STATE_PRESENTATION_SENT

    async def test_create_pres_indy_and_dif(self):
        pres_request = V20PresRequest(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[PRES_20_REQUEST][
                        V20PresFormat.Format.INDY.api
                    ],
                ),
                V20PresFormat(
                    attach_id="dif",
                    format_=ATTACHMENT_FORMAT[PRES_20_REQUEST][
                        V20PresFormat.Format.DIF.api
                    ],
                ),
            ],
            request_presentations_attach=[
                AttachDecorator.data_base64(INDY_PROOF_REQ_NAME, ident="indy"),
                AttachDecorator.data_json(DIF_PRES_REQ, ident="dif"),
            ],
        )
        px_rec_in = V20PresExRecord(pres_request=pres_request.serialize())
        more_magic_rr = async_mock.MagicMock(
            get_or_fetch_local_tails_path=async_mock.CoroutineMock(
                return_value="/tmp/sample/tails/path"
            )
        )
        with async_mock.patch.object(
            V20PresExRecord, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            test_indy_handler, "AttachDecorator", autospec=True
        ) as mock_attach_decorator_indy, async_mock.patch.object(
            test_indy_util_module, "RevocationRegistry", autospec=True
        ) as mock_rr, async_mock.patch.object(
            DIFPresFormatHandler, "create_pres", autospec=True
        ) as mock_create_pres:
            mock_rr.from_definition = async_mock.MagicMock(return_value=more_magic_rr)

            mock_attach_decorator_indy.data_base64 = async_mock.MagicMock(
                return_value=mock_attach_decorator_indy
            )

            mock_create_pres.return_value = (
                PRES_20,
                AttachDecorator.data_json(DIF_PRES, ident="dif"),
            )

            req_creds = await indy_proof_req_preview2indy_requested_creds(
                INDY_PROOF_REQ_NAME, preview=None, holder=self.holder
            )
            request_data = {"indy": req_creds, "dif": DIF_PRES_REQ}
            assert not req_creds["self_attested_attributes"]
            assert len(req_creds["requested_attributes"]) == 2
            assert len(req_creds["requested_predicates"]) == 1

            (px_rec_out, pres_msg) = await self.manager.create_pres(
                px_rec_in, request_data
            )
            save_ex.assert_called_once()
            assert px_rec_out.state == V20PresExRecord.STATE_PRESENTATION_SENT

    async def test_create_pres_proof_req_non_revoc_interval_none(self):
        indy_proof_req_vcx = deepcopy(INDY_PROOF_REQ_NAME)
        indy_proof_req_vcx["non_revoked"] = None  # simulate interop with indy-vcx
        pres_request = V20PresRequest(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[PRES_20_REQUEST][
                        V20PresFormat.Format.INDY.api
                    ],
                )
            ],
            request_presentations_attach=[
                AttachDecorator.data_base64(indy_proof_req_vcx, ident="indy")
            ],
        )
        px_rec_in = V20PresExRecord(pres_request=pres_request.serialize())

        more_magic_rr = async_mock.MagicMock(
            get_or_fetch_local_tails_path=async_mock.CoroutineMock(
                return_value="/tmp/sample/tails/path"
            )
        )
        self.profile.context.injector.bind_instance(
            BaseMultitenantManager,
            async_mock.MagicMock(MultitenantManager, autospec=True),
        )
        with async_mock.patch.object(
            IndyLedgerRequestsExecutor,
            "get_ledger_for_identifier",
            async_mock.CoroutineMock(return_value=("test_ledger_id", self.ledger)),
        ), async_mock.patch.object(
            V20PresExRecord, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            test_indy_handler, "AttachDecorator", autospec=True
        ) as mock_attach_decorator, async_mock.patch.object(
            test_indy_util_module, "RevocationRegistry", autospec=True
        ) as mock_rr:
            mock_rr.from_definition = async_mock.MagicMock(return_value=more_magic_rr)

            mock_attach_decorator.data_base64 = async_mock.MagicMock(
                return_value=mock_attach_decorator
            )

            req_creds = await indy_proof_req_preview2indy_requested_creds(
                indy_proof_req_vcx, preview=None, holder=self.holder
            )
            request_data = {"indy": req_creds}
            assert not req_creds["self_attested_attributes"]
            assert len(req_creds["requested_attributes"]) == 2
            assert len(req_creds["requested_predicates"]) == 1

            (px_rec_out, pres_msg) = await self.manager.create_pres(
                px_rec_in, request_data
            )
            save_ex.assert_called_once()
            assert px_rec_out.state == V20PresExRecord.STATE_PRESENTATION_SENT

    async def test_create_pres_self_asserted(self):
        pres_request = V20PresRequest(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[PRES_20_REQUEST][
                        V20PresFormat.Format.INDY.api
                    ],
                )
            ],
            request_presentations_attach=[
                AttachDecorator.data_base64(INDY_PROOF_REQ_SELFIE, ident="indy")
            ],
        )
        px_rec_in = V20PresExRecord(pres_request=pres_request.serialize())

        more_magic_rr = async_mock.MagicMock(
            get_or_fetch_local_tails_path=async_mock.CoroutineMock(
                return_value="/tmp/sample/tails/path"
            )
        )
        with async_mock.patch.object(
            V20PresExRecord, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            test_indy_handler, "AttachDecorator", autospec=True
        ) as mock_attach_decorator, async_mock.patch.object(
            test_indy_util_module, "RevocationRegistry", autospec=True
        ) as mock_rr:
            mock_rr.from_definition = async_mock.MagicMock(return_value=more_magic_rr)

            mock_attach_decorator.data_base64 = async_mock.MagicMock(
                return_value=mock_attach_decorator
            )

            req_creds = await indy_proof_req_preview2indy_requested_creds(
                INDY_PROOF_REQ_SELFIE, preview=None, holder=self.holder
            )
            request_data = {"indy": req_creds}

            assert len(req_creds["self_attested_attributes"]) == 3
            assert not req_creds["requested_attributes"]
            assert not req_creds["requested_predicates"]

            (px_rec_out, pres_msg) = await self.manager.create_pres(
                px_rec_in, request_data
            )
            save_ex.assert_called_once()
            assert px_rec_out.state == V20PresExRecord.STATE_PRESENTATION_SENT

    async def test_create_pres_no_revocation(self):
        Ledger = async_mock.MagicMock(BaseLedger, autospec=True)
        self.ledger = Ledger()
        self.ledger.get_schema = async_mock.CoroutineMock(
            return_value=async_mock.MagicMock()
        )
        self.ledger.get_credential_definition = async_mock.CoroutineMock(
            return_value={"value": {"revocation": None}}
        )
        self.profile.context.injector.bind_instance(BaseLedger, self.ledger)

        pres_request = V20PresRequest(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[PRES_20_REQUEST][
                        V20PresFormat.Format.INDY.api
                    ],
                )
            ],
            request_presentations_attach=[
                AttachDecorator.data_base64(INDY_PROOF_REQ_NAME, ident="indy")
            ],
        )
        px_rec_in = V20PresExRecord(pres_request=pres_request.serialize())

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
            V20PresExRecord, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            test_indy_handler, "AttachDecorator", autospec=True
        ) as mock_attach_decorator, async_mock.patch.object(
            test_indy_util_module.LOGGER, "info", async_mock.MagicMock()
        ) as mock_log_info:
            mock_attach_decorator.data_base64 = async_mock.MagicMock(
                return_value=mock_attach_decorator
            )

            req_creds = await indy_proof_req_preview2indy_requested_creds(
                INDY_PROOF_REQ_NAME, preview=None, holder=self.holder
            )
            request_data = {
                "indy": {
                    "self_attested_attributes": req_creds["self_attested_attributes"],
                    "requested_attributes": req_creds["requested_attributes"],
                    "requested_predicates": req_creds["requested_predicates"],
                }
            }

            (px_rec_out, pres_msg) = await self.manager.create_pres(
                px_rec_in, request_data
            )
            save_ex.assert_called_once()
            assert px_rec_out.state == V20PresExRecord.STATE_PRESENTATION_SENT

            # exercise superfluous timestamp removal
            for pred_reft_spec in req_creds["requested_predicates"].values():
                pred_reft_spec["timestamp"] = 1234567890
            request_data = {
                "indy": {
                    "self_attested_attributes": req_creds["self_attested_attributes"],
                    "requested_attributes": req_creds["requested_attributes"],
                    "requested_predicates": req_creds["requested_predicates"],
                }
            }
            await self.manager.create_pres(px_rec_in, request_data)
            mock_log_info.assert_called_once()

    async def test_create_pres_bad_revoc_state(self):
        pres_request = V20PresRequest(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[PRES_20_REQUEST][
                        V20PresFormat.Format.INDY.api
                    ],
                )
            ],
            request_presentations_attach=[
                AttachDecorator.data_base64(INDY_PROOF_REQ_NAME, ident="indy")
            ],
        )
        px_rec_in = V20PresExRecord(pres_request=pres_request.serialize())

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
            side_effect=test_indy_util_module.IndyHolderError(
                "Problem", {"message": "Nope"}
            )
        )
        self.profile.context.injector.bind_instance(IndyHolder, self.holder)

        more_magic_rr = async_mock.MagicMock(
            get_or_fetch_local_tails_path=async_mock.CoroutineMock(
                return_value="/tmp/sample/tails/path"
            )
        )
        with async_mock.patch.object(
            V20PresExRecord, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            test_indy_handler, "AttachDecorator", autospec=True
        ) as mock_attach_decorator, async_mock.patch.object(
            test_indy_util_module, "RevocationRegistry", autospec=True
        ) as mock_rr, async_mock.patch.object(
            test_indy_util_module.LOGGER, "error", async_mock.MagicMock()
        ) as mock_log_error:
            mock_rr.from_definition = async_mock.MagicMock(return_value=more_magic_rr)

            mock_attach_decorator.data_base64 = async_mock.MagicMock(
                return_value=mock_attach_decorator
            )
            request_data = {}
            with self.assertRaises(test_indy_util_module.IndyHolderError):
                await self.manager.create_pres(px_rec_in, request_data)

    async def test_create_pres_multi_matching_proposal_creds_names(self):
        pres_request = V20PresRequest(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[PRES_20_REQUEST][
                        V20PresFormat.Format.INDY.api
                    ],
                )
            ],
            request_presentations_attach=[
                AttachDecorator.data_base64(INDY_PROOF_REQ_NAMES, ident="indy")
            ],
        )
        px_rec_in = V20PresExRecord(pres_request=pres_request.serialize())

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
            V20PresExRecord, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            test_indy_handler, "AttachDecorator", autospec=True
        ) as mock_attach_decorator, async_mock.patch.object(
            test_indy_util_module, "RevocationRegistry", autospec=True
        ) as mock_rr:
            mock_rr.from_definition = async_mock.MagicMock(return_value=more_magic_rr)

            mock_attach_decorator.data_base64 = async_mock.MagicMock(
                return_value=mock_attach_decorator
            )

            req_creds = await indy_proof_req_preview2indy_requested_creds(
                INDY_PROOF_REQ_NAMES, preview=None, holder=self.holder
            )
            assert not req_creds["self_attested_attributes"]
            assert len(req_creds["requested_attributes"]) == 1
            assert len(req_creds["requested_predicates"]) == 1
            request_data = {"indy": req_creds}
            (px_rec_out, pres_msg) = await self.manager.create_pres(
                px_rec_in, request_data
            )
            save_ex.assert_called_once()
            assert px_rec_out.state == V20PresExRecord.STATE_PRESENTATION_SENT

    async def test_no_matching_creds_for_proof_req(self):
        pres_request = V20PresRequest(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[PRES_20_REQUEST][
                        V20PresFormat.Format.INDY.api
                    ],
                )
            ],
            request_presentations_attach=[
                AttachDecorator.data_base64(INDY_PROOF_REQ_NAMES, ident="indy")
            ],
        )
        px_rec_in = V20PresExRecord(pres_request=pres_request.serialize())
        get_creds = async_mock.CoroutineMock(return_value=())
        self.holder.get_credentials_for_presentation_request_by_referent = get_creds

        with self.assertRaises(ValueError):
            await indy_proof_req_preview2indy_requested_creds(
                INDY_PROOF_REQ_NAMES, preview=None, holder=self.holder
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
        await indy_proof_req_preview2indy_requested_creds(
            INDY_PROOF_REQ_NAMES, preview=None, holder=self.holder
        )

    async def test_no_matching_creds_indy_handler(self):
        pres_request = V20PresRequest(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[PRES_20_REQUEST][
                        V20PresFormat.Format.INDY.api
                    ],
                )
            ],
            request_presentations_attach=[
                AttachDecorator.data_base64(INDY_PROOF_REQ_NAMES, ident="indy")
            ],
        )
        px_rec_in = V20PresExRecord(pres_request=pres_request.serialize())
        get_creds = async_mock.CoroutineMock(return_value=())
        self.holder.get_credentials_for_presentation_request_by_referent = get_creds

        with async_mock.patch.object(
            V20PresExRecord, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            test_indy_handler, "AttachDecorator", autospec=True
        ) as mock_attach_decorator:
            mock_attach_decorator.data_base64 = async_mock.MagicMock(
                return_value=mock_attach_decorator
            )
            request_data = {}
            with self.assertRaises(
                test_indy_handler.V20PresFormatHandlerError
            ) as context:
                (px_rec_out, pres_msg) = await self.manager.create_pres(
                    px_rec_in, request_data
                )
            assert "No matching Indy" in str(context.exception)

    async def test_receive_pres(self):
        connection_record = async_mock.MagicMock(connection_id=CONN_ID)
        pres_proposal = V20PresProposal(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[PRES_20_PROPOSAL][
                        V20PresFormat.Format.INDY.api
                    ],
                )
            ],
            proposals_attach=[
                AttachDecorator.data_base64(INDY_PROOF_REQ_NAME, ident="indy")
            ],
        )
        pres_request = V20PresRequest(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[PRES_20_REQUEST][
                        V20PresFormat.Format.INDY.api
                    ],
                )
            ],
            request_presentations_attach=[
                AttachDecorator.data_base64(INDY_PROOF_REQ_NAME, ident="indy")
            ],
        )
        pres = V20Pres(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[PRES_20][V20PresFormat.Format.INDY.api],
                )
            ],
            presentations_attach=[
                AttachDecorator.data_base64(INDY_PROOF, ident="indy")
            ],
        )
        pres.assign_thread_id("thread-id")

        px_rec_dummy = V20PresExRecord(
            pres_proposal=pres_proposal.serialize(),
            pres_request=pres_request.serialize(),
        )

        # cover by_format property
        by_format = px_rec_dummy.by_format

        assert by_format.get("pres_proposal").get("indy") == INDY_PROOF_REQ_NAME
        assert by_format.get("pres_request").get("indy") == INDY_PROOF_REQ_NAME

        with async_mock.patch.object(
            V20PresExRecord, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            V20PresExRecord, "retrieve_by_tag_filter", autospec=True
        ) as retrieve_ex, async_mock.patch.object(
            self.profile,
            "session",
            async_mock.MagicMock(return_value=self.profile.session()),
        ) as session:
            retrieve_ex.side_effect = [px_rec_dummy]
            px_rec_out = await self.manager.receive_pres(pres, connection_record, None)
            retrieve_ex.assert_called_once_with(
                session.return_value,
                {"thread_id": "thread-id"},
                {"role": V20PresExRecord.ROLE_VERIFIER, "connection_id": CONN_ID},
            )
            save_ex.assert_called_once()
            assert px_rec_out.state == (V20PresExRecord.STATE_PRESENTATION_RECEIVED)

    async def test_receive_pres_receive_pred_value_mismatch_punt_to_indy(self):
        connection_record = async_mock.MagicMock(connection_id=CONN_ID)
        pres_proposal = V20PresProposal(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[PRES_20_PROPOSAL][
                        V20PresFormat.Format.INDY.api
                    ],
                )
            ],
            proposals_attach=[
                AttachDecorator.data_base64(INDY_PROOF_REQ_NAME, ident="indy")
            ],
        )
        indy_proof_req = deepcopy(INDY_PROOF_REQ_NAME)
        indy_proof_req["requested_predicates"]["0_highscore_GE_uuid"]["restrictions"][
            0
        ]["attr::player::value"] = "impostor"
        pres_request = V20PresRequest(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[PRES_20_REQUEST][
                        V20PresFormat.Format.INDY.api
                    ],
                )
            ],
            request_presentations_attach=[
                AttachDecorator.data_base64(indy_proof_req, ident="indy")
            ],
        )
        pres = V20Pres(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[PRES_20][V20PresFormat.Format.INDY.api],
                )
            ],
            presentations_attach=[
                AttachDecorator.data_base64(INDY_PROOF, ident="indy")
            ],
        )
        pres.assign_thread_id("thread-id")

        px_rec_dummy = V20PresExRecord(
            pres_proposal=pres_proposal.serialize(),
            pres_request=pres_request.serialize(),
        )

        # cover by_format property
        by_format = px_rec_dummy.by_format

        assert by_format.get("pres_proposal").get("indy") == INDY_PROOF_REQ_NAME
        assert by_format.get("pres_request").get("indy") == indy_proof_req

        with async_mock.patch.object(
            V20PresExRecord, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            V20PresExRecord, "retrieve_by_tag_filter", autospec=True
        ) as retrieve_ex, async_mock.patch.object(
            self.profile,
            "session",
            async_mock.MagicMock(return_value=self.profile.session()),
        ) as session:
            retrieve_ex.side_effect = [px_rec_dummy]
            px_rec_out = await self.manager.receive_pres(pres, connection_record, None)
            retrieve_ex.assert_called_once_with(
                session.return_value,
                {"thread_id": "thread-id"},
                {"role": V20PresExRecord.ROLE_VERIFIER, "connection_id": CONN_ID},
            )
            save_ex.assert_called_once()
            assert px_rec_out.state == (V20PresExRecord.STATE_PRESENTATION_RECEIVED)

    async def test_receive_pres_indy_no_predicate_restrictions(self):
        connection_record = async_mock.MagicMock(connection_id=CONN_ID)
        indy_proof_req = {
            "name": PROOF_REQ_NAME,
            "version": PROOF_REQ_VERSION,
            "nonce": PROOF_REQ_NONCE,
            "requested_attributes": {
                "0_player_uuid": {
                    "name": "player",
                    "restrictions": [{"cred_def_id": CD_ID}],
                    "non_revoked": {"from": NOW, "to": NOW},
                },
                "0_screencapture_uuid": {
                    "name": "screenCapture",
                    "restrictions": [{"cred_def_id": CD_ID}],
                    "non_revoked": {"from": NOW, "to": NOW},
                },
            },
            "requested_predicates": {
                "0_highscore_GE_uuid": {
                    "name": "highScore",
                    "p_type": ">=",
                    "p_value": 1000000,
                    "restrictions": [],
                    "non_revoked": {"from": NOW, "to": NOW},
                }
            },
        }
        pres_request = V20PresRequest(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[PRES_20_REQUEST][
                        V20PresFormat.Format.INDY.api
                    ],
                )
            ],
            request_presentations_attach=[
                AttachDecorator.data_base64(indy_proof_req, ident="indy")
            ],
        )
        pres = V20Pres(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[PRES_20][V20PresFormat.Format.INDY.api],
                )
            ],
            presentations_attach=[
                AttachDecorator.data_base64(INDY_PROOF, ident="indy")
            ],
        )
        pres.assign_thread_id("thread-id")

        px_rec_dummy = V20PresExRecord(
            pres_request=pres_request.serialize(),
        )

        # cover by_format property
        by_format = px_rec_dummy.by_format

        assert by_format.get("pres_request").get("indy") == indy_proof_req

        with async_mock.patch.object(
            V20PresExRecord, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            V20PresExRecord, "retrieve_by_tag_filter", autospec=True
        ) as retrieve_ex, async_mock.patch.object(
            self.profile,
            "session",
            async_mock.MagicMock(return_value=self.profile.session()),
        ) as session:
            retrieve_ex.side_effect = [px_rec_dummy]
            px_rec_out = await self.manager.receive_pres(pres, connection_record, None)
            retrieve_ex.assert_called_once_with(
                session.return_value,
                {"thread_id": "thread-id"},
                {"role": V20PresExRecord.ROLE_VERIFIER, "connection_id": CONN_ID},
            )
            save_ex.assert_called_once()
            assert px_rec_out.state == (V20PresExRecord.STATE_PRESENTATION_RECEIVED)

    async def test_receive_pres_indy_no_attr_restrictions(self):
        connection_record = async_mock.MagicMock(connection_id=CONN_ID)
        indy_proof_req = {
            "name": PROOF_REQ_NAME,
            "version": PROOF_REQ_VERSION,
            "nonce": PROOF_REQ_NONCE,
            "requested_attributes": {
                "0_player_uuid": {
                    "name": "player",
                    "restrictions": [],
                    "non_revoked": {"from": NOW, "to": NOW},
                }
            },
            "requested_predicates": {},
        }
        proof = deepcopy(INDY_PROOF)
        proof["requested_proof"]["revealed_attrs"] = {
            "0_player_uuid": {
                "sub_proof_index": 0,
                "raw": "Richie Knucklez",
                "encoded": "516439982",
            }
        }
        proof["requested_proof"]["predicates"] = {}
        pres_request = V20PresRequest(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[PRES_20_REQUEST][
                        V20PresFormat.Format.INDY.api
                    ],
                )
            ],
            request_presentations_attach=[
                AttachDecorator.data_base64(indy_proof_req, ident="indy")
            ],
        )
        pres = V20Pres(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[PRES_20][V20PresFormat.Format.INDY.api],
                )
            ],
            presentations_attach=[AttachDecorator.data_base64(proof, ident="indy")],
        )
        pres.assign_thread_id("thread-id")

        px_rec_dummy = V20PresExRecord(
            pres_request=pres_request.serialize(),
        )

        # cover by_format property
        by_format = px_rec_dummy.by_format

        assert by_format.get("pres_request").get("indy") == indy_proof_req

        with async_mock.patch.object(
            V20PresExRecord, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            V20PresExRecord, "retrieve_by_tag_filter", autospec=True
        ) as retrieve_ex, async_mock.patch.object(
            self.profile,
            "session",
            async_mock.MagicMock(return_value=self.profile.session()),
        ) as session:
            retrieve_ex.side_effect = [px_rec_dummy]
            px_rec_out = await self.manager.receive_pres(pres, connection_record, None)
            retrieve_ex.assert_called_once_with(
                session.return_value,
                {"thread_id": "thread-id"},
                {"role": V20PresExRecord.ROLE_VERIFIER, "connection_id": CONN_ID},
            )
            save_ex.assert_called_once()
            assert px_rec_out.state == (V20PresExRecord.STATE_PRESENTATION_RECEIVED)

    async def test_receive_pres_bait_and_switch_attr_name(self):
        connection_record = async_mock.MagicMock(connection_id=CONN_ID)
        indy_proof_req = deepcopy(INDY_PROOF_REQ_NAME)
        indy_proof_req["requested_attributes"]["0_screencapture_uuid"]["restrictions"][
            0
        ][
            "attr::screenCapture::value"
        ] = "c2NyZWVuIGNhcHR1cmUgc2hvd2luZyBzY29yZSBpbiB0aGUgbWlsbGlvbnM="
        pres_proposal = V20PresProposal(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[PRES_20_PROPOSAL][
                        V20PresFormat.Format.INDY.api
                    ],
                )
            ],
            proposals_attach=[
                AttachDecorator.data_base64(INDY_PROOF_REQ_NAME, ident="indy")
            ],
        )
        pres_request = V20PresRequest(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[PRES_20_REQUEST][
                        V20PresFormat.Format.INDY.api
                    ],
                )
            ],
            request_presentations_attach=[
                AttachDecorator.data_base64(indy_proof_req, ident="indy")
            ],
        )
        pres_x = V20Pres(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[PRES_20][V20PresFormat.Format.INDY.api],
                )
            ],
            presentations_attach=[
                AttachDecorator.data_base64(INDY_PROOF, ident="indy")
            ],
        )
        px_rec_dummy = V20PresExRecord(
            pres_proposal=pres_proposal.serialize(),
            pres_request=pres_request.serialize(),
            pres=pres_x.serialize(),
        )
        with async_mock.patch.object(
            V20PresExRecord, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            V20PresExRecord, "retrieve_by_tag_filter", autospec=True
        ) as retrieve_ex:
            retrieve_ex.return_value = px_rec_dummy
            with self.assertRaises(V20PresFormatHandlerError) as context:
                await self.manager.receive_pres(pres_x, connection_record, None)
            assert "does not satisfy proof request restrictions" in str(
                context.exception
            )

        indy_proof_req["requested_attributes"]["shenanigans"] = indy_proof_req[
            "requested_attributes"
        ].pop("0_screencapture_uuid")
        pres_proposal = V20PresProposal(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[PRES_20_PROPOSAL][
                        V20PresFormat.Format.INDY.api
                    ],
                )
            ],
            proposals_attach=[
                AttachDecorator.data_base64(indy_proof_req, ident="indy")
            ],
        )
        pres_request = V20PresRequest(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[PRES_20][V20PresFormat.Format.INDY.api],
                )
            ],
            request_presentations_attach=[
                AttachDecorator.data_base64(indy_proof_req, ident="indy")
            ],
        )
        pres_x = V20Pres(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[PRES_20][V20PresFormat.Format.INDY.api],
                )
            ],
            presentations_attach=[
                AttachDecorator.data_base64(INDY_PROOF, ident="indy")
            ],
        )

        px_rec_dummy = V20PresExRecord(
            pres_proposal=pres_proposal.serialize(),
            pres_request=pres_request.serialize(),
            pres=pres_x.serialize(),
        )
        with async_mock.patch.object(
            V20PresExRecord, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            V20PresExRecord, "retrieve_by_tag_filter", autospec=True
        ) as retrieve_ex:
            retrieve_ex.return_value = px_rec_dummy
            with self.assertRaises(V20PresFormatHandlerError) as context:
                await self.manager.receive_pres(pres_x, connection_record, None)
            assert "Presentation referent" in str(context.exception)

    async def test_receive_pres_bait_and_switch_attr_names(self):
        connection_record = async_mock.MagicMock(connection_id=CONN_ID)
        indy_proof_req = deepcopy(INDY_PROOF_REQ_NAMES)
        indy_proof_req["requested_attributes"]["0_player_uuid"]["restrictions"][0][
            "attr::screenCapture::value"
        ] = "c2NyZWVuIGNhcHR1cmUgc2hvd2luZyBzY29yZSBpbiB0aGUgbWlsbGlvbnM="
        pres_proposal = V20PresProposal(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[PRES_20_PROPOSAL][
                        V20PresFormat.Format.INDY.api
                    ],
                )
            ],
            proposals_attach=[
                AttachDecorator.data_base64(indy_proof_req, ident="indy")
            ],
        )
        pres_request = V20PresRequest(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[PRES_20_REQUEST][
                        V20PresFormat.Format.INDY.api
                    ],
                )
            ],
            request_presentations_attach=[
                AttachDecorator.data_base64(indy_proof_req, ident="indy")
            ],
        )
        pres_x = V20Pres(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[PRES_20][V20PresFormat.Format.INDY.api],
                )
            ],
            presentations_attach=[
                AttachDecorator.data_base64(INDY_PROOF_NAMES, ident="indy")
            ],
        )

        px_rec_dummy = V20PresExRecord(
            pres_proposal=pres_proposal.serialize(),
            pres_request=pres_request.serialize(),
            pres=pres_x.serialize(),
        )
        with async_mock.patch.object(
            V20PresExRecord, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            V20PresExRecord, "retrieve_by_tag_filter", autospec=True
        ) as retrieve_ex:
            retrieve_ex.return_value = px_rec_dummy
            with self.assertRaises(V20PresFormatHandlerError) as context:
                await self.manager.receive_pres(pres_x, connection_record, None)
            assert "does not satisfy proof request restrictions " in str(
                context.exception
            )

        indy_proof_req["requested_attributes"]["shenanigans"] = indy_proof_req[
            "requested_attributes"
        ].pop("0_player_uuid")
        pres_proposal = V20PresProposal(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[PRES_20_PROPOSAL][
                        V20PresFormat.Format.INDY.api
                    ],
                )
            ],
            proposals_attach=[
                AttachDecorator.data_base64(indy_proof_req, ident="indy")
            ],
        )
        pres_request = V20PresRequest(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[PRES_20][V20PresFormat.Format.INDY.api],
                )
            ],
            request_presentations_attach=[
                AttachDecorator.data_base64(indy_proof_req, ident="indy")
            ],
        )
        pres_x = V20Pres(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[PRES_20][V20PresFormat.Format.INDY.api],
                )
            ],
            presentations_attach=[
                AttachDecorator.data_base64(INDY_PROOF_NAMES, ident="indy")
            ],
        )

        px_rec_dummy = V20PresExRecord(
            pres_proposal=pres_proposal.serialize(),
            pres_request=pres_request.serialize(),
            pres=pres_x.serialize(),
        )
        with async_mock.patch.object(
            V20PresExRecord, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            V20PresExRecord, "retrieve_by_tag_filter", autospec=True
        ) as retrieve_ex:
            retrieve_ex.return_value = px_rec_dummy
            with self.assertRaises(V20PresFormatHandlerError) as context:
                await self.manager.receive_pres(pres_x, connection_record, None)
            assert "Presentation referent" in str(context.exception)

    async def test_receive_pres_bait_and_switch_pred(self):
        connection_record = async_mock.MagicMock(connection_id=CONN_ID)
        indy_proof_req = deepcopy(INDY_PROOF_REQ_NAME)
        indy_proof_req["requested_predicates"] = {}
        pres_proposal = V20PresProposal(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[PRES_20_PROPOSAL][
                        V20PresFormat.Format.INDY.api
                    ],
                )
            ],
            proposals_attach=[
                AttachDecorator.data_base64(INDY_PROOF_REQ_NAME, ident="indy")
            ],
        )
        pres_request = V20PresRequest(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[PRES_20_REQUEST][
                        V20PresFormat.Format.INDY.api
                    ],
                )
            ],
            request_presentations_attach=[
                AttachDecorator.data_base64(indy_proof_req, ident="indy")
            ],
        )
        pres_x = V20Pres(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[PRES_20][V20PresFormat.Format.INDY.api],
                )
            ],
            presentations_attach=[
                AttachDecorator.data_base64(INDY_PROOF, ident="indy")
            ],
        )

        px_rec_dummy = V20PresExRecord(
            pres_proposal=pres_proposal.serialize(),
            pres_request=pres_request.serialize(),
            pres=pres_x.serialize(),
        )
        with async_mock.patch.object(
            V20PresExRecord, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            V20PresExRecord, "retrieve_by_tag_filter", autospec=True
        ) as retrieve_ex:
            retrieve_ex.return_value = px_rec_dummy
            with self.assertRaises(V20PresFormatHandlerError) as context:
                await self.manager.receive_pres(pres_x, connection_record, None)
            assert "not in proposal request" in str(context.exception)

        indy_proof_req["requested_predicates"]["0_highscore_GE_uuid"] = {
            "name": "shenanigans",
            "p_type": ">=",
            "p_value": 1000000,
            "restrictions": [{"cred_def_id": CD_ID}],
            "non_revoked": {"from": NOW, "to": NOW},
        }
        pres_proposal = V20PresProposal(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[PRES_20_PROPOSAL][
                        V20PresFormat.Format.INDY.api
                    ],
                )
            ],
            proposals_attach=[
                AttachDecorator.data_base64(indy_proof_req, ident="indy")
            ],
        )
        pres_request = V20PresRequest(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[PRES_20][V20PresFormat.Format.INDY.api],
                )
            ],
            request_presentations_attach=[
                AttachDecorator.data_base64(indy_proof_req, ident="indy")
            ],
        )
        pres_x = V20Pres(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[PRES_20][V20PresFormat.Format.INDY.api],
                )
            ],
            presentations_attach=[
                AttachDecorator.data_base64(INDY_PROOF, ident="indy")
            ],
        )

        px_rec_dummy = V20PresExRecord(
            pres_proposal=pres_proposal.serialize(),
            pres_request=pres_request.serialize(),
            pres=pres_x.serialize(),
        )
        with async_mock.patch.object(
            V20PresExRecord, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            V20PresExRecord, "retrieve_by_tag_filter", autospec=True
        ) as retrieve_ex:
            retrieve_ex.return_value = px_rec_dummy
            with self.assertRaises(V20PresFormatHandlerError) as context:
                await self.manager.receive_pres(pres_x, connection_record, None)
            assert "shenanigans not in presentation" in str(context.exception)

        indy_proof_req["requested_predicates"]["0_highscore_GE_uuid"] = {
            "name": "highScore",
            "p_type": ">=",
            "p_value": 8000000,  # propose >= 8 million, prove >= 1 million
            "restrictions": [{"cred_def_id": CD_ID}],
            "non_revoked": {"from": NOW, "to": NOW},
        }
        pres_proposal = V20PresProposal(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[PRES_20_PROPOSAL][
                        V20PresFormat.Format.INDY.api
                    ],
                )
            ],
            proposals_attach=[
                AttachDecorator.data_base64(indy_proof_req, ident="indy")
            ],
        )
        pres_request = V20PresRequest(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[PRES_20][V20PresFormat.Format.INDY.api],
                )
            ],
            request_presentations_attach=[
                AttachDecorator.data_base64(indy_proof_req, ident="indy")
            ],
        )
        pres_x = V20Pres(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[PRES_20][V20PresFormat.Format.INDY.api],
                )
            ],
            presentations_attach=[
                AttachDecorator.data_base64(INDY_PROOF, ident="indy")
            ],
        )

        px_rec_dummy = V20PresExRecord(
            pres_proposal=pres_proposal.serialize(),
            pres_request=pres_request.serialize(),
            pres=pres_x.serialize(),
        )
        with async_mock.patch.object(
            V20PresExRecord, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            V20PresExRecord, "retrieve_by_tag_filter", autospec=True
        ) as retrieve_ex:
            retrieve_ex.return_value = px_rec_dummy
            with self.assertRaises(V20PresFormatHandlerError) as context:
                await self.manager.receive_pres(pres_x, connection_record, None)
            assert "highScore mismatches proposal request" in str(context.exception)

        indy_proof_req["requested_predicates"]["0_highscore_GE_uuid"] = {
            "name": "highScore",
            "p_type": ">=",
            "p_value": 1000000,
            "restrictions": [{"issuer_did": "FFFFFFFFFFFFFFFFFFFFFF"}],  # fake issuer
            "non_revoked": {"from": NOW, "to": NOW},
        }
        pres_proposal = V20PresProposal(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[PRES_20_PROPOSAL][
                        V20PresFormat.Format.INDY.api
                    ],
                )
            ],
            proposals_attach=[
                AttachDecorator.data_base64(indy_proof_req, ident="indy")
            ],
        )
        pres_request = V20PresRequest(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[PRES_20][V20PresFormat.Format.INDY.api],
                )
            ],
            request_presentations_attach=[
                AttachDecorator.data_base64(indy_proof_req, ident="indy")
            ],
        )
        pres_x = V20Pres(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[PRES_20][V20PresFormat.Format.INDY.api],
                )
            ],
            presentations_attach=[
                AttachDecorator.data_base64(INDY_PROOF, ident="indy")
            ],
        )

        px_rec_dummy = V20PresExRecord(
            pres_proposal=pres_proposal.serialize(),
            pres_request=pres_request.serialize(),
            pres=pres_x.serialize(),
        )
        with async_mock.patch.object(
            V20PresExRecord, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            V20PresExRecord, "retrieve_by_tag_filter", autospec=True
        ) as retrieve_ex:
            retrieve_ex.return_value = px_rec_dummy
            with self.assertRaises(V20PresFormatHandlerError) as context:
                await self.manager.receive_pres(pres_x, connection_record, None)
            assert "does not satisfy proof request restrictions " in str(
                context.exception
            )

    async def test_verify_pres(self):
        pres_request = V20PresRequest(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[PRES_20_REQUEST][
                        V20PresFormat.Format.INDY.api
                    ],
                )
            ],
            will_confirm=True,
            request_presentations_attach=[
                AttachDecorator.data_base64(INDY_PROOF_REQ_NAME, ident="indy")
            ],
        )
        pres = V20Pres(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[PRES_20][V20PresFormat.Format.INDY.api],
                )
            ],
            presentations_attach=[
                AttachDecorator.data_base64(INDY_PROOF, ident="indy")
            ],
        )
        px_rec_in = V20PresExRecord(
            pres_request=pres_request,
            pres=pres,
        )
        self.profile.context.injector.bind_instance(
            BaseMultitenantManager,
            async_mock.MagicMock(MultitenantManager, autospec=True),
        )
        with async_mock.patch.object(
            IndyLedgerRequestsExecutor,
            "get_ledger_for_identifier",
            async_mock.CoroutineMock(return_value=("test_ledger_id", self.ledger)),
        ), async_mock.patch.object(V20PresExRecord, "save", autospec=True) as save_ex:
            px_rec_out = await self.manager.verify_pres(px_rec_in)
            save_ex.assert_called_once()

            assert px_rec_out.state == (V20PresExRecord.STATE_DONE)

    async def test_verify_pres_indy_and_dif(self):
        pres_request = V20PresRequest(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[PRES_20_REQUEST][
                        V20PresFormat.Format.INDY.api
                    ],
                ),
                V20PresFormat(
                    attach_id="dif",
                    format_=ATTACHMENT_FORMAT[PRES_20_REQUEST][
                        V20PresFormat.Format.DIF.api
                    ],
                ),
            ],
            will_confirm=True,
            request_presentations_attach=[
                AttachDecorator.data_base64(INDY_PROOF_REQ_NAME, ident="indy"),
                AttachDecorator.data_json(DIF_PRES_REQ, ident="dif"),
            ],
        )
        pres = V20Pres(
            formats=[
                V20PresFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[PRES_20][V20PresFormat.Format.INDY.api],
                ),
                V20PresFormat(
                    attach_id="dif",
                    format_=ATTACHMENT_FORMAT[PRES_20][V20PresFormat.Format.DIF.api],
                ),
            ],
            presentations_attach=[
                AttachDecorator.data_base64(INDY_PROOF, ident="indy"),
                AttachDecorator.data_json(DIF_PRES, ident="dif"),
            ],
        )
        px_rec_in = V20PresExRecord(
            pres_request=pres_request,
            pres=pres,
        )

        self.profile.context.injector.bind_instance(
            DocumentLoader, custom_document_loader
        )
        self.profile.context.injector.bind_instance(
            BaseMultitenantManager,
            async_mock.MagicMock(MultitenantManager, autospec=True),
        )
        with async_mock.patch.object(
            IndyLedgerRequestsExecutor,
            "get_ledger_for_identifier",
            async_mock.CoroutineMock(return_value=("test_ledger_id", self.ledger)),
        ), async_mock.patch.object(V20PresExRecord, "save", autospec=True) as save_ex:
            px_rec_out = await self.manager.verify_pres(px_rec_in)
            save_ex.assert_called_once()

            assert px_rec_out.state == (V20PresExRecord.STATE_DONE)

        with async_mock.patch.object(
            IndyLedgerRequestsExecutor,
            "get_ledger_for_identifier",
            async_mock.CoroutineMock(return_value=("test_ledger_id", self.ledger)),
        ), async_mock.patch(
            "aries_cloudagent.vc.vc_ld.verify.verify_presentation",
            async_mock.CoroutineMock(
                return_value=PresentationVerificationResult(verified=False)
            ),
        ), async_mock.patch.object(
            IndyVerifier,
            "verify_presentation",
            async_mock.CoroutineMock(
                return_value=PresentationVerificationResult(verified=True)
            ),
        ), async_mock.patch.object(
            V20PresExRecord, "save", autospec=True
        ) as save_ex:
            px_rec_out = await self.manager.verify_pres(px_rec_in)
            save_ex.assert_called_once()
            assert px_rec_out.state == (V20PresExRecord.STATE_DONE)
            assert px_rec_out.verified == "false"

    async def test_send_pres_ack(self):
        px_rec = V20PresExRecord()

        responder = MockResponder()
        self.profile.context.injector.bind_instance(BaseResponder, responder)

        await self.manager.send_pres_ack(px_rec)
        messages = responder.messages
        assert len(messages) == 1

        px_rec = V20PresExRecord(verified="true")

        responder = MockResponder()
        self.profile.context.injector.bind_instance(BaseResponder, responder)

        await self.manager.send_pres_ack(px_rec)
        messages = responder.messages
        assert len(messages) == 1

        px_rec = V20PresExRecord(verified="false")

        responder = MockResponder()
        self.profile.context.injector.bind_instance(BaseResponder, responder)

        await self.manager.send_pres_ack(px_rec)
        messages = responder.messages
        assert len(messages) == 1

    async def test_send_pres_ack_no_responder(self):
        px_rec = V20PresExRecord()

        self.profile.context.injector.clear_binding(BaseResponder)
        await self.manager.send_pres_ack(px_rec)

    async def test_receive_pres_ack_a(self):
        conn_record = async_mock.MagicMock(connection_id=CONN_ID)

        px_rec_dummy = V20PresExRecord()
        message = async_mock.MagicMock()

        with async_mock.patch.object(
            V20PresExRecord, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            V20PresExRecord, "retrieve_by_tag_filter", autospec=True
        ) as retrieve_ex:
            retrieve_ex.return_value = px_rec_dummy
            px_rec_out = await self.manager.receive_pres_ack(message, conn_record)
            save_ex.assert_called_once()

            assert px_rec_out.state == V20PresExRecord.STATE_DONE

    async def test_receive_pres_ack_b(self):
        conn_record = async_mock.MagicMock(connection_id=CONN_ID)

        px_rec_dummy = V20PresExRecord()
        message = async_mock.MagicMock(_verification_result="true")

        with async_mock.patch.object(
            V20PresExRecord, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            V20PresExRecord, "retrieve_by_tag_filter", autospec=True
        ) as retrieve_ex:
            retrieve_ex.return_value = px_rec_dummy
            px_rec_out = await self.manager.receive_pres_ack(message, conn_record)
            save_ex.assert_called_once()

            assert px_rec_out.state == V20PresExRecord.STATE_DONE
            assert px_rec_out.verified == "true"

    async def test_receive_problem_report(self):
        connection_id = "connection-id"
        stored_exchange = V20PresExRecord(
            pres_ex_id="dummy-cxid",
            connection_id=connection_id,
            initiator=V20PresExRecord.INITIATOR_SELF,
            role=V20PresExRecord.ROLE_VERIFIER,
            state=V20PresExRecord.STATE_PROPOSAL_RECEIVED,
            thread_id="dummy-thid",
        )
        problem = V20PresProblemReport(
            description={
                "en": "Change of plans",
                "code": test_module.ProblemReportReason.ABANDONED.value,
            }
        )

        with async_mock.patch.object(
            V20PresExRecord, "save", autospec=True
        ) as save_ex, async_mock.patch.object(
            V20PresExRecord,
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

        assert stored_exchange.state == V20PresExRecord.STATE_ABANDONED

    async def test_receive_problem_report_x(self):
        connection_id = "connection-id"
        stored_exchange = V20PresExRecord(
            pres_ex_id="dummy-cxid",
            connection_id=connection_id,
            initiator=V20PresExRecord.INITIATOR_SELF,
            role=V20PresExRecord.ROLE_VERIFIER,
            state=V20PresExRecord.STATE_PROPOSAL_RECEIVED,
            thread_id="dummy-thid",
        )
        problem = V20PresProblemReport(
            description={
                "en": "Change of plans",
                "code": test_module.ProblemReportReason.ABANDONED.value,
            }
        )

        with async_mock.patch.object(
            V20PresExRecord,
            "retrieve_by_tag_filter",
            async_mock.CoroutineMock(),
        ) as retrieve_ex:
            retrieve_ex.side_effect = StorageNotFoundError("No such record")

            with self.assertRaises(StorageNotFoundError):
                await self.manager.receive_problem_report(problem, connection_id)
