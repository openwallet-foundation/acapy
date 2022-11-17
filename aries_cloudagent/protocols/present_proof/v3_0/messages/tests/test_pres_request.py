import json
from lzma import CHECK_CRC32
import pytest


from unittest import TestCase

from ......messaging.decorators.attach_decorator_didcomm_v2_pres import AttachDecorator
from ......messaging.models.base import BaseModelError
from ......messaging.util import str_to_datetime, str_to_epoch

from .....didcomm_prefix import DIDCommPrefix

from ...message_types import ATTACHMENT_FORMAT, PRES_30_REQUEST

print("before body")
from ..pres_body import V30PresBody

print("body - format")
from ..pres_format import V30PresFormat
from ..pres_request import V30PresRequest

CD_ID = f"NcYxiDXkpYi6ov5FcYDi1e:3:CL:12:tag1"
INDY_PROOF_REQ = [
    {
        "name": "proof-req",
        "version": "1.0",
        "nonce": "12345",
        "requested_attributes": {
            "0_player_uuid": {
                "name": "player",
                "restrictions": [
                    {
                        "cred_def_id": f"{CD_ID}",
                        "attr::player::value": "Richie Knucklez",
                    }
                ],
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

PRES_REQ = [
    V30PresRequest(
        body=V30PresBody(
            comment="Test",
            will_confirm=True,
        ),
        attachments=[
            AttachDecorator.data_base64(
                mapping=proof_req,
                ident="indy",
                format=V30PresFormat(
                    format_=ATTACHMENT_FORMAT[PRES_30_REQUEST][
                        V30PresFormat.Format.INDY.api
                    ],
                ),
            )
        ],
    )
    for proof_req in INDY_PROOF_REQ
]


class TestV30PresRequest(TestCase):
    """Presentation request tests."""

    def test_init_type(self):
        """Test initializer and type."""
        for i, pres_req in enumerate(PRES_REQ):
            assert pres_req.body.will_confirm  # since will_confirm == true :)
            formats = []
            for atch in pres_req.attachments:
                formats.append(atch.format)
            assert len(formats) == len(pres_req.attachments)
            assert (
                pres_req.attachments[0].content == INDY_PROOF_REQ[i]
            )  # (content is a @property function of attach-decorators)
            assert pres_req.attachment(V30PresFormat.Format.INDY) == INDY_PROOF_REQ[i]
            assert pres_req._type == DIDCommPrefix.qualify_current(
                PRES_30_REQUEST
            )  # should be ok

    def test_attachment_no_target_format(self):
        """Test attachment behaviour for only unknown formats."""

        x_pres_req = V30PresRequest(
            body=V30PresBody(comment="Test"),
            # formats=[V30PresFormat(attach_id="not_indy", format_="not_indy")],
            attachments=[
                AttachDecorator.data_base64(
                    ident="not_indy",
                    mapping=PRES_REQ[0].serialize(),
                    format=V30PresFormat(attach_id="not_indy", format_="not_indy"),
                )
            ],
        )
        # error because function requ-msg calls format.get-att
        # but given a one format, now without id, no
        assert x_pres_req.attachment() is None

    def test_serde(self):
        """Test de/serialization."""
        for pres_req_msg in PRES_REQ:
            pres_req_dict = pres_req_msg.serialize()
            pres_req_obj = V30PresRequest.deserialize(pres_req_dict)
            assert type(pres_req_obj) == V30PresRequest

            pres_req_dict["attachments"][0]["data"]["base64"] = "eyJub3QiOiAiaW5keSJ9"
            with self.assertRaises(BaseModelError):
                V30PresRequest.deserialize(pres_req_dict)

            pres_req_dict["attachments"][0]["id"] = "xxx"
            with self.assertRaises(BaseModelError):
                V30PresRequest.deserialize(pres_req_dict)

            pres_req_dict["attachments"].append(
                {
                    "id": "def",
                    "media-type": "application/json",
                    "data": {"base64": "eyJub3QiOiAiaW5keSJ9"},
                    "format": "",
                }
            )  # more attachments than formats
            with self.assertRaises(BaseModelError):
                V30PresRequest.deserialize(pres_req_dict)

            obj = pres_req_msg.serialize()
            obj["attachments"].append(
                {
                    "id": "not_indy",
                    "media-type": "application/json",
                    "data": {"base64": "eyJub3QiOiAiaW5keSJ9"},
                    "format": "<V30PresFormat(format_='not_indy')>",
                }
            )
            V30PresRequest.deserialize(obj)
