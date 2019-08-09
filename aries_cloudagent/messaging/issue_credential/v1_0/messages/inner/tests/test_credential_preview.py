from unittest import TestCase

from ....message_types import CREDENTIAL_PREVIEW
from ..credential_preview import (
    CredentialAttrPreview,
    CredentialPreview,
    CredentialPreviewSchema
)


CRED_PREVIEW = CredentialPreview(
    attributes=(
        CredentialAttrPreview.list_plain({'test': '123', 'hello': 'world'}) +
        [
            CredentialAttrPreview(
                name='icon',
                value='cG90YXRv',
                encoding='base64',
                mime_type='image/png'
            )
        ]
    )
)


class TestCredentialAttrPreview(TestCase):
    """Attribute preview tests"""

    def test_eq(self):
        attr_previews_none_plain = [
            CredentialAttrPreview(
                name="item",
                value="value"
            ),
            CredentialAttrPreview(
                name="item",
                value="value",
                encoding=None,
                mime_type=None
            ),
            CredentialAttrPreview(
                name="item",
                value="value",
                encoding=None,
                mime_type="text/plain"
            ),
            CredentialAttrPreview(
                name="item",
                value="value",
                encoding=None,
                mime_type="TEXT/PLAIN"
            )
        ]
        attr_previews_b64_plain = [
            CredentialAttrPreview(
                name="item",
                value="dmFsdWU=",
                encoding="base64"
            ),
            CredentialAttrPreview(   
                name="item",
                value="dmFsdWU=",
                encoding="base64",
                mime_type=None
            ),
            CredentialAttrPreview(
                name="item",
                value="dmFsdWU=",
                encoding="base64",
                mime_type="text/plain"
            ),
            CredentialAttrPreview(
                name="item",
                value="dmFsdWU=",
                encoding="BASE64",
                mime_type="text/plain"
            ),
            CredentialAttrPreview(
                name="item",
                value="dmFsdWU=",
                encoding="base64",
                mime_type="TEXT/PLAIN"
            )
        ]
        attr_previews_different = [
            CredentialAttrPreview(
                name="item",
                value="dmFsdWU=",
                encoding="base64",
                mime_type="image/png"
            ),
            CredentialAttrPreview(
                name="item",
                value="distinct value",
                mime_type=None
            ),
            CredentialAttrPreview(
                name="distinct_name",
                value="distinct value",
                mime_type=None
            ),
            CredentialAttrPreview(
                name="item",
                value="xyzzy"
            )
        ]

        for lhs in attr_previews_none_plain:
            for rhs in attr_previews_b64_plain:
                assert lhs == rhs  # values decode to same

        for lhs in attr_previews_none_plain:
            for rhs in attr_previews_different:
                assert lhs != rhs

        for lhs in attr_previews_b64_plain:
            for rhs in attr_previews_different:
                assert lhs != rhs

        for lidx in range(len(attr_previews_none_plain) - 1):
            for ridx in range(lidx + 1, len(attr_previews_none_plain)):
                assert attr_previews_none_plain[lidx] == attr_previews_none_plain[ridx]

        for lidx in range(len(attr_previews_b64_plain) - 1):
            for ridx in range(lidx + 1, len(attr_previews_b64_plain)):
                assert attr_previews_b64_plain[lidx] == attr_previews_b64_plain[ridx]

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
        assert CRED_PREVIEW._type == CREDENTIAL_PREVIEW

    def test_preview(self):
        """Test preview for attr-dict and metadata utilities."""
        assert CRED_PREVIEW.attr_dict(decode=False) == {
            'test': '123',
            'hello': 'world',
            'icon': 'cG90YXRv'
        }
        assert CRED_PREVIEW.attr_dict(decode=True) == {
            'test': '123',
            'hello': 'world',
            'icon': 'potato'
        }
        assert CRED_PREVIEW.metadata() == {
            'test': {
            },
            'hello': {
            },
            'icon': {
                'mime-type': 'image/png',
                'encoding': 'base64'
            }
        }

    def test_deserialize(self):
        """Test deserialize."""
        obj = {
            '@type': CREDENTIAL_PREVIEW,
            'attributes': [
                {
                    'name': 'name',
                    'mime-type': 'text/plain',
                    'value': 'Alexander Delarge'
                },
                {
                    'name': 'pic',
                    'mime-type': 'image/png',
                    'encoding': 'base64',
                    'value': 'Abcd0123...'
                }
            ]
        }

        cred_preview = CredentialPreview.deserialize(obj)
        assert type(cred_preview) == CredentialPreview

    def test_serialize(self):
        """Test serialization."""

        cred_preview_dict = CRED_PREVIEW.serialize()
        assert cred_preview_dict == {
            "@type": CREDENTIAL_PREVIEW,
            "attributes": [
                {
                    "name": "test",
                    "value": "123"
                },
                {
                    "name": "hello",
                    "value": "world"
                },
                {
                    "name": "icon",
                    "mime-type": "image/png",
                    "encoding": "base64",
                    "value": "cG90YXRv"
                }
            ]
        }


class TestCredentialPreviewSchema(TestCase):
    """Test credential cred preview schema."""

    def test_make_model(self):
        """Test making model."""
        data = CRED_PREVIEW.serialize()
        model_instance = CredentialPreview.deserialize(data)
        assert isinstance(model_instance, CredentialPreview)
