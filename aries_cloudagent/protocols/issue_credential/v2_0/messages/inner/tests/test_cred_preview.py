from unittest import TestCase

from ......didcomm_prefix import DIDCommPrefix

from ....message_types import CRED_20_PREVIEW

from ..cred_preview import (
    V20CredAttrSpec,
    V20CredPreview,
)

TEST_PREVIEW = V20CredPreview(
    attributes=(
        V20CredAttrSpec.list_plain({"test": "123", "hello": "world"})
        + [V20CredAttrSpec(name="icon", value="cG90YXRv", mime_type="image/PNG")]
    )
)


class TestV20CredAttrSpec(TestCase):
    """Attribute preview tests"""

    def test_eq(self):
        attr_previews_none_plain = [
            V20CredAttrSpec(name="item", value="value"),
            V20CredAttrSpec(name="item", value="value", mime_type=None),
        ]
        attr_previews_different = [
            V20CredAttrSpec(name="item", value="dmFsdWU=", mime_type="image/png"),
            V20CredAttrSpec(name="item", value="distinct value"),
            V20CredAttrSpec(
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


class TestV20CredPreview(TestCase):
    """Presentation preview tests."""

    def test_init(self):
        """Test initializer."""
        assert TEST_PREVIEW.attributes

    def test_type(self):
        """Test type."""
        assert TEST_PREVIEW._type == DIDCommPrefix.qualify_current(CRED_20_PREVIEW)

    def test_preview(self):
        """Test preview for attr-dict and metadata utilities."""
        assert TEST_PREVIEW.attr_dict(decode=False) == {
            "test": "123",
            "hello": "world",
            "icon": "cG90YXRv",
        }
        assert TEST_PREVIEW.attr_dict(decode=True) == {
            "test": "123",
            "hello": "world",
            "icon": "potato",
        }
        assert TEST_PREVIEW.mime_types() == {
            "icon": "image/png"  # canonicalize to lower case
        }

    def test_deserialize(self):
        """Test deserialize."""
        obj = {
            "@type": CRED_20_PREVIEW,
            "attributes": [
                {"name": "name", "value": "Alexander Delarge"},
                {"name": "pic", "mime-type": "image/png", "value": "Abcd0123..."},
            ],
        }

        cred20_preview = V20CredPreview.deserialize(obj)
        assert type(cred20_preview) == V20CredPreview

    def test_serialize(self):
        """Test serialization."""

        cred20_preview_dict = TEST_PREVIEW.serialize()
        assert cred20_preview_dict == {
            "@type": DIDCommPrefix.qualify_current(CRED_20_PREVIEW),
            "attributes": [
                {"name": "test", "value": "123"},
                {"name": "hello", "value": "world"},
                {"name": "icon", "mime-type": "image/png", "value": "cG90YXRv"},
            ],
        }


class TestV20CredPreviewSchema(TestCase):
    """Test schema."""

    def test_make_model(self):
        """Test making model."""
        data = TEST_PREVIEW.serialize()
        model_instance = V20CredPreview.deserialize(data)
        assert isinstance(model_instance, V20CredPreview)
