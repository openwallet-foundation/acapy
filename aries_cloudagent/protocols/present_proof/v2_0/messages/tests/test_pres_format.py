from unittest import TestCase

from marshmallow import ValidationError

from ......messaging.decorators.attach_decorator import AttachDecorator

from ..pres_format import V20PresFormat
from ....util.presentation_preview import PresentationPreview


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


class TestV20FormatFormat(TestCase):
    """Coverage for self-get."""

    def test_get_completeness(self):
        assert (
            V20PresFormat.Format.get(V20PresFormat.Format.INDY)
            is V20PresFormat.Format.INDY
        )
        assert V20PresFormat.Format.get("no such format") is None
        assert V20PresFormat.Format.get("Indy") is V20PresFormat.Format.INDY
        assert V20PresFormat.Format.get("HL/INDY").aries == "hlindy-zkp-v1.0"
        assert "indy" in V20PresFormat.Format.get("HL/INDY").aka
        assert (
            V20PresFormat.Format.get("JSON-LD").aries
            == "dif/presentation-exchange/definitions@v1.0"
        )

    def test_validate_proposal_attach_x(self):
        with self.assertRaises(ValidationError) as context:
            V20PresFormat.INDY.validate_proposal_attach(
                data="not even close"
            )
        assert "Invalid presentation proposal attachment" in str(context.exception)

    def test_get_attachment_data(self):
        assert (
            V20PresFormat.Format.INDY.get_attachment_data(
                formats=[
                    V20PresFormat(attach_id="abc", format_=V20PresFormat.Format.INDY)
                ],
                attachments=[
                    AttachDecorator.from_indy_dict(
                        PRES_PREVIEW.serialize(),
                        ident="abc",
                    )
                ],
            )
            == PRES_PREVIEW
        )

        assert (
            V20PresFormat.Format.INDY.get_attachment_data(
                formats=[
                    V20PresFormat(attach_id="abc", format_=V20PresFormat.Format.INDY)
                ],
                attachments=[
                    AttachDecorator.from_indy_dict(
                        PRES_PREVIEW.serialize(),
                        ident="xxx",
                    )
                ],
            )
            is None
        )

        assert (
            V20PresFormat.Format.DIF.get_attachment_data(
                formats=[
                    V20PresFormat(attach_id="abc", format_=V20PresFormat.Format.INDY)
                ],
                attachments=[
                    AttachDecorator.from_indy_dict(
                        PRES_PREVIEW.serialize(),
                        ident="abc",
                    )
                ],
            )
            is None
        )
