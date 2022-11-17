from re import M
from unittest import TestCase

from marshmallow import ValidationError

from aries_cloudagent.protocols.issue_credential.v3_0.messages.inner.cred_preview import V30CredAttrSpec, V30CredPreview, V30CredPreviewBody

from ......indy.models.pres_preview import (
    IndyPresAttrSpec,
    IndyPresPreview,
    IndyPresPredSpec,
)
from ......messaging.decorators.attach_decorator_didcomm_v2_cred import AttachDecorator

from ..cred_body import V30CredBody

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

TEST_PREVIEW = V30CredPreview(
    _body=V30CredPreviewBody(
    attributes=(
        V30CredAttrSpec.list_plain({"test": "123", "hello": "world"})
        + [V30CredAttrSpec(name="icon", value="cG90YXRv", mime_type="image/png")]
    )
    )
)

class TestV30FormatFormat(TestCase):
    """Coverage for self-get."""

    def test_init_type(self):
        """Test initializer, type."""
        my_test_body = V30CredBody(comment= "My Comment", replacement_id="x", credential_preview=TEST_PREVIEW)
        assert my_test_body.comment =="My Comment"
        assert my_test_body.replacement_id == "x"

        assert my_test_body.credential_preview is not None
        assert my_test_body.credential_preview._body.attributes== TEST_PREVIEW._body.attributes
