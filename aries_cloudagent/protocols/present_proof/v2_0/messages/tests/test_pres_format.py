from unittest import TestCase

from marshmallow import ValidationError

from ......messaging.decorators.attach_decorator import AttachDecorator

from ....indy.presentation_preview import (
    IndyPresAttrSpec,
    IndyPresentationPreview,
    IndyPresPredSpec,
)

from ..pres_format import V20PresFormat


S_ID = "NcYxiDXkpYi6ov5FcYDi1e:2:vidya:1.0"
CD_ID = f"NcYxiDXkpYi6ov5FcYDi1e:3:CL:{S_ID}:tag1"
PRES_PREVIEW = IndyPresentationPreview(
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
            V20PresFormat.Format.INDY.validate_proposal_attach(data="not even close")

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
            == PRES_PREVIEW.serialize()
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
