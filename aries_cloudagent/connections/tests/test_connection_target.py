from unittest import TestCase

from ..models.connection_target import ConnectionTarget


class TestConnectionTarget(TestCase):

    def test_target(self):
        target = ConnectionTarget(
            did="did",
            endpoint="endpoint",
            label="label",
            recipient_keys=None,
            routing_keys=["abc123"],
            sender_key=None
        )
        assert target.did == "did"
        assert target.endpoint == "endpoint"
        assert target.label == "label"
        assert target.recipient_keys == []
        assert target.routing_keys == ["abc123"]
        assert target.sender_key is None
