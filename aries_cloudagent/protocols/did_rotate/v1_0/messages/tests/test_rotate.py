from unittest import TestCase, mock

from ......protocols.didcomm_prefix import DIDCommPrefix
from ...message_types import PROTOCOL_PACKAGE, ROTATE
from ...messages.rotate import Rotate

TEST_DID = "test-did"


class TestRotate(TestCase):

    def test_init_type(self):
        """Test initializer."""

        obj = Rotate(to_did=TEST_DID)
        assert obj._type == DIDCommPrefix.qualify_current(ROTATE)

    @mock.patch(f"{PROTOCOL_PACKAGE}.messages.rotate.RotateSchema.load")
    def test_deserialize(self, mock_rotate_schema_load):
        """Test deserialization."""

        obj = Rotate(to_did=TEST_DID)
        rotate = Rotate.deserialize(obj)
        mock_rotate_schema_load.assert_called_once_with(obj)
        assert rotate is mock_rotate_schema_load.return_value

    @mock.patch(f"{PROTOCOL_PACKAGE}.messages.rotate.RotateSchema.dump")
    def test_serialize(self, mock_rotate_schema_dump):
        """Test serialization."""

        obj = Rotate(to_did=TEST_DID)
        rotate_dict = obj.serialize()
        mock_rotate_schema_dump.assert_called_once_with(obj)
        assert rotate_dict is mock_rotate_schema_dump.return_value

    def test_serde(self):
        obj = {
            "to_did": TEST_DID,
        }
        rotate = Rotate.deserialize(obj)
        assert rotate._type == DIDCommPrefix.qualify_current(ROTATE)

        rotate_dict = rotate.serialize()
        assert rotate_dict["to_did"] == obj["to_did"]

    def test_make_model(self):
        """Test making model."""

        obj = Rotate(to_did=TEST_DID)
        data = obj.serialize()
        model_instance = Rotate.deserialize(data)
        assert isinstance(model_instance, Rotate)
