from unittest import TestCase

from ......didcomm_prefix import DIDCommPrefix

from ....message_types import CRED_30_PREVIEW

from ..cred_preview import (
    V30CredAttrSpec,
    V30CredPreview,
    V30CredPreviewBody,
)

TEST_PREVIEW = V30CredPreview(
    _body=V30CredPreviewBody(
        attributes=(
            V30CredAttrSpec.list_plain({"test": "123", "hello": "world"})
            + [V30CredAttrSpec(name="icon", value="cG90YXRv", mime_type="image/PNG")]
        )
    )
)


class TestV30CredAttrSpec(TestCase):
    """Attribute preview tests"""

    def test_eq(self):
        attr_previews_none_plain = [
            V30CredAttrSpec(name="item", value="value"),
            V30CredAttrSpec(name="item", value="value", mime_type=None),
        ]
        attr_previews_different = [
            V30CredAttrSpec(name="item", value="dmFsdWU=", mime_type="image/png"),
            V30CredAttrSpec(name="item", value="distinct value"),
            V30CredAttrSpec(
                name="distinct_name", value="distinct value", mime_type=None
            ),
        ]

        for lhs in attr_previews_none_plain:
            for rhs in attr_previews_different:
                assert lhs != rhs

        for lidx in range(len(attr_previews_none_plain) - 1):
            for ridx in range(lidx + 1, len(attr_previews_none_plain)):
                assert attr_previews_none_plain[lidx] == attr_previews_none_plain[ridx]

        for lidx in range(len(attr_previews_different) - 1):
            for ridx in range(lidx + 1, len(attr_previews_different)):
                assert attr_previews_different[lidx] != attr_previews_different[ridx]


class TestV30CredPreview(TestCase):
    """Presentation preview tests."""

    def test_init(self):
        """Test initializer."""
        assert TEST_PREVIEW._body.attributes

    # def test_type(self):
    #     """Test type."""
    #     assert TEST_PREVIEW._type == DIDCommPrefix.qualify_current(CRED_30_PREVIEW)

    def test_preview(self):
        """Test preview for attr-dict and metadata utilities."""
        assert TEST_PREVIEW._body.attr_dict(decode=False) == {
            "test": "123",
            "hello": "world",
            "icon": "cG90YXRv",
        }
        assert TEST_PREVIEW._body.attr_dict(decode=True) == {
            "test": "123",
            "hello": "world",
            "icon": "potato",
        }
        assert TEST_PREVIEW._body.mime_types() == {
            "icon": "image/png"  # canonicalize to lower case
        }

    def test_deserialize(self):
        """Test deserialize."""
        obj = {
            "type": CRED_30_PREVIEW,
            "body": {
                "attributes": [
                    {"name": "name", "value": "Alexander Delarge"},
                    {"name": "pic", "mime-type": "image/png", "value": "Abcd0123..."},
                ],
            },
        }

        cred20_preview = V30CredPreview.deserialize(obj)
        assert type(cred20_preview) == V30CredPreview

    def test_serialize(self):
        """Test serialization."""

        cred30_preview_dict = TEST_PREVIEW.serialize()
        assert cred30_preview_dict == {
            "type": "issue-credential/3.0/credential-preview",
            "body": {
                "attributes": [
                    {"name": "test", "value": "123"},
                    {"name": "hello", "value": "world"},
                    {"name": "icon", "media-type": "image/png", "value": "cG90YXRv"},
                ],
            },
        }


class TestV30CredPreviewSchema(TestCase):
    """Test schema."""

    def test_make_model(self):
        """Test making model."""
        data = TEST_PREVIEW.serialize()
        model_instance = V30CredPreview.deserialize(data)
        assert isinstance(model_instance, V30CredPreview)
