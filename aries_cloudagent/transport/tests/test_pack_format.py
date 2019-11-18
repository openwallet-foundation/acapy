import json

from asynctest import TestCase as AsyncTestCase, mock as async_mock

from ...config.injection_context import InjectionContext
from ...protocols.routing.message_types import FORWARD
from ...wallet.base import BaseWallet
from ...wallet.basic import BasicWallet

from ..error import MessageParseError
from ..pack_format import PackWireFormat


class TestPackWireFormat(AsyncTestCase):
    test_message_type = "PROTOCOL/MESSAGE"
    test_message_id = "MESSAGE_ID"
    test_content = "CONTENT"
    test_thread_id = "THREAD_ID"
    test_message = {
        "@type": test_message_type,
        "@id": test_message_id,
        "~thread": {"thid": test_thread_id},
        "~transport": {"return_route": "all"},
        "content": test_content,
    }
    test_seed = "testseed000000000000000000000001"
    test_routing_seed = "testseed000000000000000000000002"

    def setUp(self):
        self.wallet = BasicWallet()
        self.context = InjectionContext()
        self.context.injector.bind_instance(BaseWallet, self.wallet)

    async def test_errors(self):
        serializer = PackWireFormat()

        bad_values = [None, "", "1", "[]", "{..."]

        for message_json in bad_values:
            with self.assertRaises(MessageParseError):
                message_dict, delivery = await serializer.parse_message(
                    self.context, message_json
                )

    async def test_unpacked(self):
        serializer = PackWireFormat()
        message_json = json.dumps(self.test_message)
        message_dict, delivery = await serializer.parse_message(
            self.context, message_json
        )
        assert message_dict == self.test_message
        assert message_dict["@type"] == self.test_message_type
        assert delivery.thread_id == self.test_thread_id
        assert delivery.direct_response_mode == "all"

    async def test_fallback(self):
        serializer = PackWireFormat()

        message = self.test_message.copy()
        message.pop("@type")
        message_json = json.dumps(message)

        message_dict, delivery = await serializer.parse_message(
            self.context, message_json
        )
        assert delivery.raw_message == message_json
        assert message_dict == message

    async def test_encode_decode(self):
        local_did = await self.wallet.create_local_did(self.test_seed)
        serializer = PackWireFormat()
        recipient_keys = (local_did.verkey,)
        routing_keys = ()
        sender_key = local_did.verkey
        message_json = json.dumps(self.test_message)

        packed_json = await serializer.encode_message(
            self.context, message_json, recipient_keys, routing_keys, sender_key
        )
        packed = json.loads(packed_json)

        assert isinstance(packed, dict) and "protected" in packed

        message_dict, delivery = await serializer.parse_message(
            self.context, packed_json
        )
        assert message_dict == self.test_message
        assert message_dict["@type"] == self.test_message_type
        assert delivery.thread_id == self.test_thread_id
        assert delivery.direct_response_mode == "all"

    async def test_forward(self):
        local_did = await self.wallet.create_local_did(self.test_seed)
        router_did = await self.wallet.create_local_did(self.test_routing_seed)
        serializer = PackWireFormat()
        recipient_keys = (local_did.verkey,)
        routing_keys = (router_did.verkey,)
        sender_key = local_did.verkey
        message_json = json.dumps(self.test_message)

        packed_json = await serializer.encode_message(
            self.context, message_json, recipient_keys, routing_keys, sender_key
        )
        packed = json.loads(packed_json)

        assert isinstance(packed, dict) and "protected" in packed

        message_dict, delivery = await serializer.parse_message(
            self.context, packed_json
        )
        assert message_dict["@type"] == FORWARD
        assert delivery.recipient_verkey == router_did.verkey
        assert delivery.sender_verkey is None
