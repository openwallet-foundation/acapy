import json

from datetime import datetime, timezone
from unittest import TestCase

from .....didcomm_prefix import DIDCommPrefix

from ...message_types import PRES_30_ACK

from ..pres_ack import V30PresAck


class TestV30PresAck(TestCase):
    """Presentation ack tests."""

    def test_init(self):
        """Test initializer."""
        pres_ack = V30PresAck()
        assert pres_ack.status == "OK"

    def test_type(self):
        """Test type."""
        pres_ack = V30PresAck()
        assert pres_ack._type == DIDCommPrefix.qualify_current(PRES_30_ACK)

    def test_deserialize(self):
        """Test deserialization."""
        dump = json.dumps(
            {"@type": DIDCommPrefix.qualify_current(PRES_30_ACK), "status": "OK"}
        )

        pres_ack = V30PresAck.deserialize(dump)
        assert type(pres_ack) == V30PresAck

    def test_serialize(self):
        """Test serialization."""
        pres_ack_dict = V30PresAck().serialize()
        pres_ack_dict.pop("@id")

        assert pres_ack_dict == {
            "@type": DIDCommPrefix.qualify_current(PRES_30_ACK),
            "status": "OK",
        }


class TestV30PresAckSchema(TestCase):
    """Test presentation ack schema"""

    def test_make_model(self):
        """Test making model."""
        pres_ack_dict = V30PresAck().serialize()
        """
        Looks like: {
            "@type": ".../present-proof/1.0/ack",
            "@id": "f49773e3-bd56-4868-a5f1-456d1e6d1a16",
            "status": "OK"
        }
        """

        model_instance = V30PresAck.deserialize(pres_ack_dict)
        assert isinstance(model_instance, V30PresAck)
