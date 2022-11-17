from asynctest import TestCase as AsyncTestCase

from ..connection_target import ConnectionTarget

TEST_DID = "55GkHamhTU1ZbTbV2ab9DE"
TEST_VERKEY = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
TEST_ENDPOINT = "http://localhost"


class TestConnectionTarget(AsyncTestCase):
    def test_deser(self):
        target = ConnectionTarget(
            did=TEST_DID,
            endpoint=TEST_ENDPOINT,
            label="a label",
            recipient_keys=[TEST_VERKEY],
            routing_keys=[TEST_VERKEY],
            sender_key=TEST_VERKEY,
        )
        serial = target.serialize()
        serial["extra-stuff"] = "to exclude"
        deser = ConnectionTarget.deserialize(serial)

        assert deser.did == target.did
        assert deser.endpoint == target.endpoint
        assert deser.label == target.label
        assert deser.recipient_keys == target.recipient_keys
        assert deser.routing_keys == target.routing_keys
        assert deser.sender_key == target.sender_key
