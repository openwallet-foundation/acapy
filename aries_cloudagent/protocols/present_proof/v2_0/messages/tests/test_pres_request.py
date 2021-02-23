import json
import pytest

from datetime import datetime, timezone
from unittest import TestCase

from ......messaging.decorators.attach_decorator import AttachDecorator
from ......messaging.models.base import BaseModelError
from ......messaging.util import str_to_datetime, str_to_epoch

from .....didcomm_prefix import DIDCommPrefix

from ....indy.presentation_preview import PRESENTATION_PREVIEW

from ...message_types import PRES_20_REQUEST

from ..pres_format import V20PresFormat
from ..pres_request import V20PresRequest, V20PresRequestSchema


NOW_8601 = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat(" ", "seconds")
NOW_EPOCH = str_to_epoch(NOW_8601)
CD_ID = "GMm4vMw8LLrLJjp81kRRLp:3:CL:12:tag"
INDY_PROOF_REQ = json.loads(
    f"""{{
    "name": "proof-req",
    "version": "1.0",
    "nonce": "12345",
    "requested_attributes": {{
        "0_player_uuid": {{
            "name": "player",
            "restrictions": [
                {{
                    "cred_def_id": "{CD_ID}"
                }}
            ],
            "non_revoked": {{
                "from": {NOW_EPOCH},
                "to": {NOW_EPOCH}
            }}
        }},
        "0_screencapture_uuid": {{
            "name": "screenCapture",
            "restrictions": [
                {{
                    "cred_def_id": "{CD_ID}"
                }}
            ],
            "non_revoked": {{
                "from": {NOW_EPOCH},
                "to": {NOW_EPOCH}
            }}
        }}
    }},
    "requested_predicates": {{
        "0_highscore_GE_uuid": {{
            "name": "highScore",
            "p_type": ">=",
            "p_value": 1000000,
            "restrictions": [
                {{
                    "cred_def_id": "{CD_ID}"
                }}
            ],
            "non_revoked": {{
                "from": {NOW_EPOCH},
                "to": {NOW_EPOCH}
            }}
        }}
    }}
}}"""
)

PRES_REQ = V20PresRequest(
    comment="Test",
    will_confirm=True,
    formats=[
        V20PresFormat(
            attach_id="abc",
            format_=V20PresFormat.Format.INDY.aries,
        )
    ],
    request_presentations_attach=[
        AttachDecorator.data_base64(
            mapping=INDY_PROOF_REQ,
            ident="abc",
        )
    ],
)


class TestV20PresRequest(TestCase):
    """Presentation request tests."""

    def test_init_type(self):
        """Test initializer, type."""
        assert PRES_REQ.will_confirm
        assert len(PRES_REQ.formats) == len(PRES_REQ.request_presentations_attach)
        assert PRES_REQ.request_presentations_attach[0].content == INDY_PROOF_REQ
        assert PRES_REQ.attachment(V20PresFormat.Format.INDY) == INDY_PROOF_REQ
        assert PRES_REQ._type == DIDCommPrefix.qualify_current(PRES_20_REQUEST)

    def test_deserialize(self):
        """Test deserialization."""
        dump = json.dumps(
            {
                "@type": DIDCommPrefix.qualify_current(PRES_20_REQUEST),
                "comment": "Hello World",
                "will_confirm": True,
                "formats": [
                    {
                        "attach_id": "abc",
                        "format": V20PresFormat.Format.INDY.aries,
                    }
                ],
                "request_presentations~attach": [
                    AttachDecorator.data_base64(
                        mapping=INDY_PROOF_REQ,
                        ident="abc",
                    ).serialize()
                ],
            }
        )

        pres_request = V20PresRequest.deserialize(dump)
        assert type(pres_request) == V20PresRequest

    def test_deserialize_x(self):
        """Test deserialization failures."""
        dump_x = json.dumps(
            {
                "@type": DIDCommPrefix.qualify_current(PRES_20_REQUEST),
                "comment": "Hello World",
                "will_confirm": True,
                "formats": [
                    {
                        "attach_id": "abc",
                        "format": V20PresFormat.Format.INDY.aries,
                    }
                ],
                "request_presentations~attach": [],
            }
        )
        with pytest.raises(BaseModelError):
            V20PresRequest.deserialize(dump_x)

        dump_x = json.dumps(
            {
                "@type": DIDCommPrefix.qualify_current(PRES_20_REQUEST),
                "comment": "Hello World",
                "will_confirm": True,
                "formats": [
                    {
                        "attach_id": "abc",
                        "format": V20PresFormat.Format.INDY.aries,
                    }
                ],
                "request_presentations~attach": [
                    AttachDecorator.data_base64(
                        mapping=INDY_PROOF_REQ,
                        ident="def",
                    ).serialize()
                ],
            }
        )
        with pytest.raises(BaseModelError):
            V20PresRequest.deserialize(dump_x)

    def test_serialize(self):
        """Test serialization."""
        pres_req_dict = PRES_REQ.serialize()
        pres_req_dict.pop("@id")

        serialized = {
            "@type": DIDCommPrefix.qualify_current(PRES_20_REQUEST),
            "will_confirm": True,
            "formats": [
                {
                    "attach_id": "abc",
                    "format": V20PresFormat.Format.INDY.aries,
                }
            ],
            "request_presentations~attach": [
                AttachDecorator.data_base64(
                    mapping=INDY_PROOF_REQ,
                    ident="abc",
                ).serialize()
            ],
            "comment": "Test",
        }
        assert pres_req_dict == serialized


class TestV20PresRequestSchema(TestCase):
    """Test presentation request schema"""

    def test_make_model(self):
        """Test making model."""
        pres_req_dict = PRES_REQ.serialize()
        """
        Looks like: {
            "@type": "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/present-proof/2.0/..."
            "@id": "...",
            "will_confirm": true,
            "request_presentations~attach": [
                {
                    "@id": "abc",
                    "mime-type": "application/json",
                    "data": {
                        "base64": "eyJu..."
                    }
                }
            ],
            "formats": [
                {
                    "attach_id": "abc",
                    "format": "hlindy-zkp-v1.0"
                }
            ],
            "comment": "Test"
        }
        """

        model_instance = PRES_REQ.deserialize(pres_req_dict)
        assert isinstance(model_instance, V20PresRequest)
