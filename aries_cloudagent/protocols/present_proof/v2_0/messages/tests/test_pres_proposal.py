from unittest import TestCase

from ......messaging.decorators.attach_decorator import AttachDecorator
from ......messaging.models.base import BaseModelError

from .....didcomm_prefix import DIDCommPrefix

from ....util.presentation_preview import (
    PresAttrSpec,
    PresPredSpec,
    PRESENTATION_PREVIEW, 
    PresentationPreview,
)

from ...message_types import PRES_20_PROPOSAL

from ..pres_format import V20PresFormat
from ..pres_proposal import V20PresProposal


S_ID = "NcYxiDXkpYi6ov5FcYDi1e:2:vidya:1.0"
CD_ID = f"NcYxiDXkpYi6ov5FcYDi1e:3:CL:{S_ID}:tag1"
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


class TestV20PresProposal(TestCase):
    """Presentation proposal tests."""

    def test_init_type_attachment(self):
        """Test initializer, type, attachment."""
        pres_proposal = V20PresProposal(
            comment="Hello World",
            formats=[
                V20PresFormat(
                    attach_id="abc",
                    format_=V20PresFormat.Format.INDY.aries,
                )
            ],
            proposal_attach=[
                AttachDecorator.from_indy_dict(PRES_PREVIEW.serialize(), ident="abc")
            ],
        )
        assert pres_proposal._type == DIDCommPrefix.qualify_current(PRES_20_PROPOSAL)
        assert (
            pres_proposal.attachment(V20PresFormat.Format.INDY)
            == PRES_PREVIEW.serialize()
        )

    def test_serde(self):
        """Test de/serialization."""
        pres_proposal = V20PresProposal(
            comment="Hello World",
            formats=[
                V20PresFormat(
                    attach_id="abc",
                    format_=V20PresFormat.Format.INDY.aries,
                )
            ],
            proposal_attach=[
                AttachDecorator.from_indy_dict(PRES_PREVIEW.serialize(), ident="abc")
            ],
        )
        pres_proposal_ser = pres_proposal.serialize()
        pres_proposal_deser = V20PresProposal.deserialize(pres_proposal_ser)
        assert type(pres_proposal_deser) == V20PresProposal

        pres_proposal_dict = pres_proposal_deser.serialize()
        pres_proposal_dict.pop("@id")

        assert pres_proposal_dict == pres_proposal_ser
