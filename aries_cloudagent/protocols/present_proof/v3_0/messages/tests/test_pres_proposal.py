import pytest

from unittest import TestCase

from ......messaging.decorators.attach_decorator_didcomm_v2_pres import AttachDecorator
from ......messaging.models.base import BaseModelError

from .....didcomm_prefix import DIDCommPrefix

from ...message_types import ATTACHMENT_FORMAT, PRES_30_PROPOSAL

from ..pres_format import V30PresFormat
from ..pres_body import V30PresBody
from ..pres_proposal import V30PresProposal

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


class TestV30PresProposal(TestCase):
    """Presentation proposal tests."""

    def test_init_type_attachment_serde(self):
        """Test initializer, type, attachment, de/serialization."""
        for proof_req in INDY_PROOF_REQ:
            pres_proposal = V30PresProposal(
                body=V30PresBody(comment="Hello World"),
                attachments=[
                    AttachDecorator.data_base64(
                        proof_req,
                        ident="indy",
                        format=V30PresFormat(
                            format_=ATTACHMENT_FORMAT[PRES_30_PROPOSAL][
                                V30PresFormat.Format.INDY.api
                            ],
                        ),
                    )
                ],
            )

            print(pres_proposal.attachments[0].format)
            assert pres_proposal._type == DIDCommPrefix.qualify_current(
                PRES_30_PROPOSAL
            )
            assert pres_proposal.attachment(V30PresFormat.Format.INDY) == proof_req

            pres_proposal_ser = pres_proposal.serialize()
            pres_proposal_deser = V30PresProposal.deserialize(pres_proposal_ser)
            assert type(pres_proposal_deser) == V30PresProposal

            pres_proposal_dict = pres_proposal_deser.serialize()
            assert pres_proposal_dict == pres_proposal_ser

            obj = pres_proposal.serialize()
            obj["attachments"].append(
                {
                    "id": "not_indy",
                    "media-type": "application/json",
                    "data": {"base64": "eyJub3QiOiAiaW5keSJ9"},
                    "format": "<V30PresFormat(format_='hlindy/proof-req@v2.0')>",
                }
            )

            V30PresProposal.deserialize(obj)

    def test_attachment_no_target_format(self):
        """Test attachment behaviour for only unknown formats."""

        x_pres_proposal = V30PresProposal(
            body=V30PresBody(comment="Test"),
            # formats=[V30PresFormat(attach_id="not_indy", format_="not_indy")],
            attachments=[
                AttachDecorator.data_base64(
                    ident="not_indy",
                    mapping=INDY_PROOF_REQ[0],
                    format=V30PresFormat(format_="not_indy"),
                )
            ],
        )
        assert x_pres_proposal.attachment() is None
