from unittest import mock, TestCase

from asynctest import TestCase as AsyncTestCase

from .....didcomm_prefix import DIDCommPrefix

from ...message_types import PING
from ..ping import Ping


class TestPing(TestCase):
    def setUp(self):
        self.test_comment = "hello"
        self.test_response_requested = True
        self.test_ping = Ping(
            comment=self.test_comment, response_requested=self.test_response_requested
        )

    def test_init(self):
        """Test initialization."""
        assert self.test_ping.comment == self.test_comment
        assert self.test_ping.response_requested == self.test_response_requested

    def test_type(self):
        """Test type."""
        assert self.test_ping._type == DIDCommPrefix.qualify_current(PING)

    @mock.patch(
        "aries_cloudagent.protocols.trustping.v1_0.messages.ping.PingSchema.load"
    )
    def test_deserialize(self, mock_ping_schema_load):
        """
        Test deserialization.
        """
        obj = {"obj": "obj"}

        msg = Ping.deserialize(obj)
        mock_ping_schema_load.assert_called_once_with(obj)

        assert msg is mock_ping_schema_load.return_value

    @mock.patch(
        "aries_cloudagent.protocols.trustping.v1_0.messages.ping.PingSchema.dump"
    )
    def test_serialize(self, mock_ping_schema_load):
        """
        Test serialization.
        """
        msg_dict = self.test_ping.serialize()
        mock_ping_schema_load.assert_called_once_with(self.test_ping)

        assert msg_dict is mock_ping_schema_load.return_value


class TestPingSchema(AsyncTestCase):
    """Test ping schema."""

    async def test_make_model(self):
        ping = Ping(comment="hello", response_requested=True)
        data = ping.serialize()
        model_instance = Ping.deserialize(data)
        assert type(model_instance) is type(ping)
