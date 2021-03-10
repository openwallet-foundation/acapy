import json

from datetime import datetime, timezone
from unittest import TestCase

from .....didcomm_prefix import DIDCommPrefix

from ...message_types import PRES_20_ACK

from ..pres_ack import V20PresAck


class TestV20PresAck(TestCase):
    """Presentation ack tests."""

    def test_init(self):
        """Test initializer."""
        pres_ack = V20PresAck()
        assert pres_ack.status == "OK"

    def test_type(self):
        """Test type."""
        pres_ack = V20PresAck()
        assert pres_ack._type == DIDCommPrefix.qualify_current(PRES_20_ACK)

    def test_deserialize(self):
        """Test deserialization."""
        dump = json.dumps(
            {"@type": DIDCommPrefix.qualify_current(PRES_20_ACK), "status": "OK"}
        )

        pres_ack = V20PresAck.deserialize(dump)
        assert type(pres_ack) == V20PresAck

    def test_serialize(self):
        """Test serialization."""
        pres_ack_dict = V20PresAck().serialize()
        pres_ack_dict.pop("@id")

        assert pres_ack_dict == {
            "@type": DIDCommPrefix.qualify_current(PRES_20_ACK),
            "status": "OK",
        }


class TestV20PresAckSchema(TestCase):
    """Test presentation ack schema"""

    def test_make_model(self):
        """Test making model."""
        pres_ack_dict = V20PresAck().serialize()
        """
        Looks like: {
            "@type": ".../present-proof/1.0/ack",
            "@id": "f49773e3-bd56-4868-a5f1-456d1e6d1a16",
            "status": "OK"
        }
        """

        model_instance = V20PresAck.deserialize(pres_ack_dict)
        assert isinstance(model_instance, V20PresAck)
