from unittest import TestCase

from ....message_types import CREDENTIAL_PREVIEW
from ..credential_preview import (
    AttributePreview,
    CredentialPreview,
    CredentialPreviewSchema
)


CRED_PREVIEW = CredentialPreview(
    attributes=(
        AttributePreview.list_plain({'test': '123', 'hello': 'world'}) +
        [
            AttributePreview(
                name='icon',
                value='cG90YXRv',
                encoding='base64',
                mime_type='image/png'
            )
        ]
    )
)


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
                'mime-type': 'text/plain'
            },
            'hello': {
                'mime-type': 'text/plain'
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
                    "mime-type": "text/plain",
                    "value": "123"
                },
                {
                    "name": "hello",
                    "mime-type": "text/plain",
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
