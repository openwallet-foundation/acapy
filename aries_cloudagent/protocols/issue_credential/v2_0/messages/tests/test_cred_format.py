from unittest import TestCase

from ......messaging.decorators.attach_decorator import AttachDecorator

from ..cred_format import V20CredFormat
from ..inner.cred_preview import V20CredAttrSpec, V20CredPreview


TEST_PREVIEW = V20CredPreview(
    attributes=(
        V20CredAttrSpec.list_plain({"test": "123", "hello": "world"})
        + [V20CredAttrSpec(name="icon", value="cG90YXRv", mime_type="image/png")]
    )
)

TEST_INDY_FILTER = {
    "schema_id": "GMm4vMw8LLrLJjp81kRRLp:2:ahoy:1560364003.0",
    "cred_def_id": "GMm4vMw8LLrLJjp81kRRLp:3:CL:12:tag",
}


class TestV20FormatFormat(TestCase):
    """Coverage for self-get."""

    def test_get_completeness(self):
        assert (
            V20CredFormat.Format.get(V20CredFormat.Format.INDY)
            is V20CredFormat.Format.INDY
        )
        assert V20CredFormat.Format.get("no such format") is None
        assert V20CredFormat.Format.get("hlindy/...") is V20CredFormat.Format.INDY
        assert (
            V20CredFormat.Format.get("aries/...").detail.__name__
            == "V20CredExRecordLDProof"
        )
        assert (
            V20CredFormat.Format.get(V20CredFormat.Format.LD_PROOF.api)
            is V20CredFormat.Format.LD_PROOF
        )

    def test_get_attachment_data(self):
        assert (
            V20CredFormat.Format.INDY.get_attachment_data(
                formats=[
                    V20CredFormat(attach_id="indy", format_=V20CredFormat.Format.INDY)
                ],
                attachments=[
                    AttachDecorator.data_base64(TEST_INDY_FILTER, ident="indy")
                ],
            )
            == TEST_INDY_FILTER
        )

        assert (
            V20CredFormat.Format.INDY.get_attachment_data(
                formats=[
                    V20CredFormat(attach_id="indy", format_=V20CredFormat.Format.INDY)
                ],
                attachments=[
                    AttachDecorator.data_base64(TEST_INDY_FILTER, ident="xxx")
                ],
            )
            is None
        )

        assert (
            V20CredFormat.Format.LD_PROOF.get_attachment_data(
                formats=[
                    V20CredFormat(attach_id="indy", format_=V20CredFormat.Format.INDY)
                ],
                attachments=[
                    AttachDecorator.data_base64(TEST_INDY_FILTER, ident="indy")
                ],
            )
            is None
        )
