from unittest import TestCase, mock

from ......messaging.models.base import BaseModelError
from .....didcomm_prefix import DIDCommPrefix
from ...message_types import ACK, PROTOCOL_PACKAGE
from ..ack import RotateAck

THID = "test-thid"
PTHID = "test-pthid"


class TestRotateAck(TestCase):
    def test_init_type(self):
        """Test initializer."""

        obj = RotateAck()
        assert obj._type == DIDCommPrefix.qualify_current(ACK)

    @mock.patch(f"{PROTOCOL_PACKAGE}.messages.ack.RotateAckSchema.load")
    def test_deserialize(self, mock_rotate_ack_schema_load):
        """Test deserialization."""

        obj = RotateAck()
        rotate_ack = RotateAck.deserialize(obj)
        mock_rotate_ack_schema_load.assert_called_once_with(obj)
        assert rotate_ack is mock_rotate_ack_schema_load.return_value

    @mock.patch(f"{PROTOCOL_PACKAGE}.messages.ack.RotateAckSchema.dump")
    def test_serialize(self, mock_rotate_ack_schema_dump):
        """Test serialization."""

        obj = RotateAck()
        rotate_ack_dict = obj.serialize()
        mock_rotate_ack_schema_dump.assert_called_once_with(obj)
        assert rotate_ack_dict is mock_rotate_ack_schema_dump.return_value

    def test_serde(self):
        obj = {"~thread": {"thid": THID, "pthid": PTHID}, "status": "OK"}
        rotate_ack = RotateAck.deserialize(obj)
        assert rotate_ack._type == DIDCommPrefix.qualify_current(ACK)

        rotate_ack_dict = rotate_ack.serialize()
        assert rotate_ack_dict["~thread"] == obj["~thread"]

    def test_make_model(self):
        """Test making model."""

        obj = RotateAck()
        obj.assign_thread_id(THID, PTHID)
        rotate_ack_dict = obj.serialize()
        rotate_ack = RotateAck.deserialize(rotate_ack_dict)
        assert isinstance(rotate_ack, RotateAck)

    def test_make_model_fails_no_thread(self):
        """Test making model with no thread attachment."""

        obj = RotateAck()
        with self.assertRaises(BaseModelError):
            rotate_ack_dict = obj.serialize()
