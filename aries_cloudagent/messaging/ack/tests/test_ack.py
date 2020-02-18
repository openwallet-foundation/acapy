from unittest import mock, TestCase

from ..message import Ack


class TestAck(TestCase):
    """Ack tests"""

    def test_no(self):
        """Test: do not instantiate ack; subclass per protocol"""
        with self.assertRaises(AttributeError):
            ack = Ack()
