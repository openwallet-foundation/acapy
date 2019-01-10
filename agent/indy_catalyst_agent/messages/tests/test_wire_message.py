from ..wire_message import WireMessage

from unittest import mock, TestCase


class TestWireMessage(TestCase):
    to = "to"
    _from = "from"
    msg = "msg"

    def test_init(self):
        wire_message = WireMessage(self._from, self.to, self.msg)
        assert wire_message._from == self._from
        assert wire_message.to == self.to
        assert wire_message.msg == self.msg
