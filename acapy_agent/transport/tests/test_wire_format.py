from unittest import IsolatedAsyncioTestCase

from ..wire_format import JsonWireFormat


class TestWireFormat(IsolatedAsyncioTestCase):
    async def test_get_recipient_keys(self):
        serializer = JsonWireFormat()
        recipient_keys = serializer.get_recipient_keys("message_body")

        # JSON wire format always returns empty array
        self.assertEqual(recipient_keys, [])
