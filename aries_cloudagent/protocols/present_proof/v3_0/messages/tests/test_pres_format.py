from unittest import TestCase

from marshmallow import ValidationError

from ......indy.models.pres_preview import (
    IndyPresAttrSpec,
    IndyPresPreview,
    IndyPresPredSpec,
)
from ......messaging.decorators.attach_decorator_didcomm_v2_pres import AttachDecorator

from ..pres_format import V30PresFormat

CD_ID = "GMm4vMw8LLrLJjp81kRRLp:3:CL:12:tag"
INDY_PROOF_REQ = [
    {
        "name": "proof-req",
        "version": "1.0",
        "nonce": "12345",
        "requested_attributes": {
            "0_player_uuid": {
                "name": "player",
                "restrictions": [{"cred_def_id": f"{CD_ID}"}],
                "non_revoked": {
                    "from": 1234567890,
                    "to": 1234567890,
                },
            },
            "0_screencapture_uuid": {
                "name": "screenCapture",
                "restrictions": [{"cred_def_id": f"{CD_ID}"}],
                "non_revoked": {
                    "from": 1234567890,
                    "to": 1234567890,
                },
            },
        },
        "requested_predicates": {
            "0_highscore_GE_uuid": {
                "name": "highScore",
                "p_type": ">=",
                "p_value": 1000000,
                "restrictions": [{"cred_def_id": f"{CD_ID}"}],
                "non_revoked": {
                    "from": 1234567890,
                    "to": 1234567890,
                },
            }
        },
    },
    {
        "name": "proof-req",
        "version": "1.0",
        "nonce": "123456",
        "requested_attributes": {
            "0_player_uuid": {
                "name": "player",
                "restrictions": [{"cred_def_id": f"{CD_ID}"}],
            },
            "0_screencapture_uuid": {
                "name": "screenCapture",
                "restrictions": [{"cred_def_id": f"{CD_ID}"}],
            },
        },
        "requested_predicates": {
            "0_highscore_GE_uuid": {
                "name": "highScore",
                "p_type": ">=",
                "p_value": 1000000,
                "restrictions": [{"cred_def_id": f"{CD_ID}"}],
            }
        },
    },
    {
        "name": "proof-req",
        "version": "1.0",
        "nonce": "1234567",
        "requested_attributes": {},
        "requested_predicates": {
            "0_highscore_GE_uuid": {
                "name": "highScore",
                "p_type": ">=",
                "p_value": 1000000,
                "restrictions": [{"cred_def_id": f"{CD_ID}"}],
            }
        },
    },
]


class TestV30FormatFormat(TestCase):
    """Coverage for self-get."""

    def test_get_completeness(self):
        assert (
            V30PresFormat.Format.get(V30PresFormat.Format.INDY)
            is V30PresFormat.Format.INDY
        )
        assert V30PresFormat.Format.get("no such format") is None
        assert V30PresFormat.Format.get("hlindy/...") is V30PresFormat.Format.INDY
        assert (
            V30PresFormat.Format.get(V30PresFormat.Format.DIF.api)
            is V30PresFormat.Format.DIF
        )
