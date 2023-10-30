from unittest import TestCase

from ......didcomm_prefix import DIDCommPrefix

from ....message_types import CREDENTIAL_PREVIEW

from ..credential_preview import (
    CredAttrSpec,
    CredentialPreview,
)

CRED_PREVIEW = CredentialPreview(
    attributes=(
        CredAttrSpec.list_plain({"test": "123", "hello": "world"})
        + [CredAttrSpec(name="icon", value="cG90YXRv", mime_type="image/PNG")]
    )
)


class TestCredAttrSpec(TestCase):
    """Attribute preview tests"""

    def test_eq(self):
        attr_previews_none_plain = [
            CredAttrSpec(name="item", value="value"),
            CredAttrSpec(name="item", value="value", mime_type=None),
        ]
        attr_previews_different = [
            CredAttrSpec(name="item", value="dmFsdWU=", mime_type="image/png"),
            CredAttrSpec(name="item", value="distinct value"),
            CredAttrSpec(name="distinct_name", value="distinct value", mime_type=None),
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


class TestCredentialPreview(TestCase):
    """Presentation preview tests."""

    def test_init(self):
        """Test initializer."""
        assert CRED_PREVIEW.attributes

    def test_type(self):
        """Test type."""
        assert CRED_PREVIEW._type == DIDCommPrefix.qualify_current(CREDENTIAL_PREVIEW)

    def test_preview(self):
        """Test preview for attr-dict and metadata utilities."""
        assert CRED_PREVIEW.attr_dict(decode=False) == {
            "test": "123",
            "hello": "world",
            "icon": "cG90YXRv",
        }
        assert CRED_PREVIEW.attr_dict(decode=True) == {
            "test": "123",
            "hello": "world",
            "icon": "potato",
        }
        assert CRED_PREVIEW.mime_types() == {
            "icon": "image/png"  # canonicalize to lower case
        }

    def test_deserialize(self):
        """Test deserialize."""
        obj = {
            "@type": CREDENTIAL_PREVIEW,
            "attributes": [
                {"name": "name", "value": "Alexander Delarge"},
                {"name": "pic", "mime-type": "image/png", "value": "Abcd0123..."},
            ],
        }

        cred_preview = CredentialPreview.deserialize(obj)
        assert type(cred_preview) == CredentialPreview

    def test_serialize(self):
        """Test serialization."""

        cred_preview_dict = CRED_PREVIEW.serialize()
        assert cred_preview_dict == {
            "@type": DIDCommPrefix.qualify_current(CREDENTIAL_PREVIEW),
            "attributes": [
                {"name": "test", "value": "123"},
                {"name": "hello", "value": "world"},
                {"name": "icon", "mime-type": "image/png", "value": "cG90YXRv"},
            ],
        }


class TestCredentialPreviewSchema(TestCase):
    """Test credential cred preview schema."""

    def test_make_model(self):
        """Test making model."""
        data = CRED_PREVIEW.serialize()
        model_instance = CredentialPreview.deserialize(data)
        assert isinstance(model_instance, CredentialPreview)
