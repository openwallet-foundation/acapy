from unittest import TestCase

#from ......messaging.decorators.attach_decorator import AttachDecorator

from ..cred_format import V30CredFormat
from ..inner.cred_preview import V30CredAttrSpec, V30CredPreview, V30CredPreviewBody


TEST_PREVIEW = V30CredPreview(
    _body=V30CredPreviewBody(
    attributes=(
        V30CredAttrSpec.list_plain({"test": "123", "hello": "world"})
        + [V30CredAttrSpec(name="icon", value="cG90YXRv", mime_type="image/png")]
    )
    )
)

TEST_INDY_FILTER = {
    "schema_id": "GMm4vMw8LLrLJjp81kRRLp:2:ahoy:1560364003.0",
    "cred_def_id": "GMm4vMw8LLrLJjp81kRRLp:3:CL:12:tag",
}


class TestV30FormatFormat(TestCase):
    """Coverage for self-get."""

    def test_get_completeness(self):
        assert (
            V30CredFormat.Format.get(V30CredFormat.Format.INDY)
            is V30CredFormat.Format.INDY
        )
        assert V30CredFormat.Format.get("no such format") is None
        assert V30CredFormat.Format.get("hlindy/...") is V30CredFormat.Format.INDY
        assert (
            V30CredFormat.Format.get("aries/...").detail.__name__
            == "V30CredExRecordLDProof"
        )
        assert (
            V30CredFormat.Format.get(V30CredFormat.Format.LD_PROOF.api)
            is V30CredFormat.Format.LD_PROOF
        )
