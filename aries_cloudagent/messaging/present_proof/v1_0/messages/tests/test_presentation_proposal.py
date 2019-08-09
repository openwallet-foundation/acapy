from ..presentation_proposal import PresentationProposal
from ..inner.presentation_preview import PresentationAttrPreview, PresentationPreview
from ...message_types import PRESENTATION_PREVIEW, PRESENTATION_PROPOSAL

from unittest import TestCase


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
                "highScore": "1000000"
            }
        }
    },
    non_revocation_times={}
)


class TestPresentationProposal(TestCase):
    """Presentation proposal tests."""

    def test_init(self):
        """Test initializer."""
        presentation_proposal = PresentationProposal(
            comment="Hello World",
            presentation_proposal=PRES_PREVIEW
        )
        assert presentation_proposal.presentation_proposal == PRES_PREVIEW

    def test_type(self):
        """Test type."""
        presentation_proposal = PresentationProposal(
            comment="Hello World",
            presentation_proposal=PRES_PREVIEW
        )
        assert presentation_proposal._type == PRESENTATION_PROPOSAL

    def test_deserialize(self):
        """Test deserialization."""
        obj = {
            "@type": PRESENTATION_PROPOSAL,
            "comment": "Hello World",
            "presentation_proposal": {
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
                "non_revocation_times": {}
            }
        }

        pres_proposal = PresentationProposal.deserialize(obj)
        assert type(pres_proposal) == PresentationProposal

    def test_serialize(self):
        """Test serialization."""

        pres_proposal = PresentationProposal(
            comment="Hello World",
            presentation_proposal=PRES_PREVIEW
        )

        pres_proposal_dict = pres_proposal.serialize()
        pres_proposal_dict.pop("@id")

        assert pres_proposal_dict == {
            "@type": PRESENTATION_PROPOSAL,
            "comment": "Hello World",
            "presentation_proposal": {
                "@type": PRESENTATION_PREVIEW,
                "attributes": {
                    CD_ID: {
                        "player": {
                            "value": "Richie Knucklez",
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
                "non_revocation_times": {}
            }
        }

class TestPresentationProposalSchema(TestCase):
    """Test presentation cred proposal schema."""

    presentation_proposal = PresentationProposal(
        comment="Hello World",
        presentation_proposal=PRES_PREVIEW
    )

    def test_make_model(self):
        """Test making model."""
        data = self.presentation_proposal.serialize()
        model_instance = PresentationProposal.deserialize(data)
        assert isinstance(model_instance, PresentationProposal)
