from copy import deepcopy
from datetime import datetime, timezone
from unittest import TestCase

import json

from .......messaging.util import str_to_datetime, str_to_epoch
from ....message_types import PRESENTATION_PREVIEW
from ..presentation_preview import (
    PresentationAttrPreview,
    PresentationPreview,
    PresentationPreviewSchema
)

NOW_8601 = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat(" ", "seconds")
NOW_EPOCH = str_to_epoch(NOW_8601)
CD_ID = "GMm4vMw8LLrLJjp81kRRLp:3:CL:12:tag"
PRES_PREVIEW = PresentationPreview(
    attributes={
        CD_ID: {
            "player": PresentationAttrPreview(value="Richie Knucklez"),
            "screenCapture": PresentationAttrPreview(
                mime_type="image/png",
                encoding="base64",
                value="aW1hZ2luZSBhIHNjcmVlbiBjYXB0dXJl"
            )
        }
    },
    predicates={
        CD_ID: {
            ">=": {
                "highScore": 1000000
            }
        }
    },
    non_revocation_times={
        CD_ID: NOW_8601
    }
)
INDY_PROOF_REQ = json.loads(f"""{{
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
}}""")


class TestPresentationAttrPreview(TestCase):
    """Attribute preview tests"""

    def test_eq(self):
        attr_previews_none_plain = [
            PresentationAttrPreview(value="value"),
            PresentationAttrPreview(value="value", encoding=None, mime_type=None),
            PresentationAttrPreview(
                value="value",
                encoding=None,
                mime_type="text/plain"
            ),
            PresentationAttrPreview(
                value="value",
                encoding=None,
                mime_type="TEXT/PLAIN"
            )
        ]
        attr_previews_b64_plain = [
            PresentationAttrPreview(value="dmFsdWU=", encoding="base64"),
            PresentationAttrPreview(   
                value="dmFsdWU=",
                encoding="base64",
                mime_type=None
            ),
            PresentationAttrPreview(
                value="dmFsdWU=",
                encoding="base64",
                mime_type="text/plain"
            ),
            PresentationAttrPreview(
                value="dmFsdWU=",
                encoding="BASE64",
                mime_type="text/plain"
            ),
            PresentationAttrPreview(
                value="dmFsdWU=",
                encoding="base64",
                mime_type="TEXT/PLAIN"
            )
        ]
        attr_previews_different = [
            PresentationAttrPreview(
                value="dmFsdWU=",
                encoding="base64",
                mime_type="image/png"
            ),
            PresentationAttrPreview(
                value="distinct value",
                mime_type=None
            ),
            PresentationAttrPreview()
        ]

        for lhs in attr_previews_none_plain:
            for rhs in attr_previews_b64_plain:
                assert lhs == rhs  # values decode to same

        for lhs in attr_previews_none_plain:
            for rhs in attr_previews_different:
                assert lhs != rhs

        for lhs in attr_previews_b64_plain:
            for rhs in attr_previews_different:
                assert lhs != rhs

        for lidx in range(len(attr_previews_none_plain) - 1):
            for ridx in range(lidx + 1, len(attr_previews_none_plain)):
                assert attr_previews_none_plain[lidx] == attr_previews_none_plain[ridx]

        for lidx in range(len(attr_previews_b64_plain) - 1):
            for ridx in range(lidx + 1, len(attr_previews_b64_plain)):
                assert attr_previews_b64_plain[lidx] == attr_previews_b64_plain[ridx]

        for lidx in range(len(attr_previews_different) - 1):
            for ridx in range(lidx + 1, len(attr_previews_different)):
                assert attr_previews_different[lidx] != attr_previews_different[ridx]


class TestPresentationPreview(TestCase):
    """Presentation preview tests"""

    def test_init(self):
        """Test initializer."""
        assert PRES_PREVIEW.attributes
        assert PRES_PREVIEW.predicates
        assert PRES_PREVIEW.non_revocation_times

    def test_type(self):
        """Test type."""
        assert PRES_PREVIEW._type == PRESENTATION_PREVIEW

    def test_indy_proof_request(self):
        """Test to and from indy proof request."""

        pres_preview = deepcopy(PRES_PREVIEW)
        pres_preview.void_attribute_previews()

        assert (
            pres_preview == PresentationPreview.from_indy_proof_request(INDY_PROOF_REQ)
        )
        assert pres_preview.indy_proof_request(
            **{k: INDY_PROOF_REQ[k] for k in ("name", "version", "nonce")}
        ) == INDY_PROOF_REQ
        assert PRES_PREVIEW.indy_proof_request(
            **{k: INDY_PROOF_REQ[k] for k in ("name", "version", "nonce")}
        ) == INDY_PROOF_REQ

    def test_preview(self):
        """Test preview for attr-values and attr-metadata utilities."""
        assert PRES_PREVIEW.attr_dict(decode=False) == {
            CD_ID: {
                "player": "Richie Knucklez",
                "screenCapture": "aW1hZ2luZSBhIHNjcmVlbiBjYXB0dXJl"
            }
        }
        assert PRES_PREVIEW.attr_dict(decode=True) == {
            CD_ID: {
                "player": "Richie Knucklez",
                "screenCapture": "imagine a screen capture"
            }
        }
        assert PRES_PREVIEW.attr_metadata() == {
            CD_ID: {
                "player": {},
                "screenCapture": {
                    "mime-type": "image/png",
                    "encoding": "base64"
                }
            }
        }
        assert PRES_PREVIEW.indy_proof_request("proof-req", "1.0", "12345") == {
            "name": "proof-req",
            "version": "1.0",
            "nonce": "12345",
            "requested_attributes": {
                "0_player_uuid": {
                    "name": "player",
                    "restrictions": [
                        {
                            "cred_def_id": CD_ID
                        }
                    ],
                    "non_revoked": {
                        "from": NOW_EPOCH,
                        "to": NOW_EPOCH
                    }
                },
                "0_screencapture_uuid": {
                    "name": "screenCapture",
                    "restrictions": [
                        {
                            "cred_def_id": CD_ID
                        }
                    ],
                    "non_revoked": {
                        "from": NOW_EPOCH,
                        "to": NOW_EPOCH
                    }
                }
            },
            "requested_predicates": {
                "0_highscore_GE_uuid": {
                    "name": "highScore",
                    "p_type": ">=",
                    "p_value": 1000000,
                    "restrictions": [
                        {
                            "cred_def_id": CD_ID
                        }
                    ],
                    "non_revoked": {
                        "from": NOW_EPOCH,
                        "to": NOW_EPOCH
                    }
                }
            }
        }

    def test_deserialize(self):
        """Test deserialization."""
        dump = {
            "@type": PRESENTATION_PREVIEW,
            "attributes": {
                CD_ID: {
                    "player": {
                        "value": "Richie Knucklez"
                    },
                    "screenCapture": {
                        "value": "aW1hZ2luZSBhIHNjcmVlbiBjYXB0dXJl",
                        "encoding": "base64",
                        "mime-type": "image/png"
                    }
                }
            },
            "predicates": {
                CD_ID: {
                    ">=": {
                        "highScore": 1000000
                    }
                }
            },
            "non_revocation_times": {
                CD_ID: NOW_8601
            }
        }

        preview = PresentationPreview.deserialize(dump)
        assert type(preview) == PresentationPreview

    def test_serialize(self):
        """Test serialization."""

        preview_dict = PRES_PREVIEW.serialize()
        assert preview_dict == {
            "@type": PRESENTATION_PREVIEW,
            "attributes": {
                CD_ID: {
                    "player": {
                        "value": "Richie Knucklez"
                    },
                    "screenCapture": {
                        "value": "aW1hZ2luZSBhIHNjcmVlbiBjYXB0dXJl",
                        "encoding": "base64",
                        "mime-type": "image/png"
                    }
                }
            },
            "predicates": {
                CD_ID: {
                    ">=": {
                        "highScore": 1000000
                    }
                }
            },
            "non_revocation_times": {
                CD_ID: NOW_8601
            }
        }


class TestPresentationPreviewSchema(TestCase):
    """Test presentation preview schema"""

    def test_make_model(self):
        """Test making model."""
        data = PRES_PREVIEW.serialize()
        model_instance = PresentationPreview.deserialize(data)
        assert isinstance(model_instance, PresentationPreview)
