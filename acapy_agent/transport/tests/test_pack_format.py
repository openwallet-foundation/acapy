import json
from base64 import b64encode
from unittest import IsolatedAsyncioTestCase

from didcomm_messaging import DIDCommMessaging, PackResult
from didcomm_messaging.crypto.backend.askar import CryptoServiceError

from ...protocols.didcomm_prefix import DIDCommPrefix
from ...protocols.routing.v1_0.message_types import FORWARD
from ...tests import mock
from ...transport.inbound.receipt import MessageReceipt
from ...transport.v2_pack_format import V2PackWireFormat
from ...utils.testing import create_test_profile
from ...wallet.base import BaseWallet
from ...wallet.did_method import SOV, DIDMethods
from ...wallet.error import WalletError
from ...wallet.key_type import ED25519
from .. import pack_format as test_module
from ..error import RecipientKeysError, WireFormatEncodeError, WireFormatParseError
from ..pack_format import PackWireFormat


class TestPackWireFormat(IsolatedAsyncioTestCase):
    test_message_type = DIDCommPrefix.qualify_current("PROTOCOL/MESSAGE")
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

    async def asyncSetUp(self):
        self.profile = await create_test_profile()
        self.profile.context.injector.bind_instance(DIDMethods, DIDMethods())

    async def test_errors(self):
        serializer = PackWireFormat()
        bad_values = [None, "", "1", "[]", "{..."]

        async with self.profile.session() as session:
            for message_json in bad_values:
                with self.assertRaises(WireFormatParseError):
                    await serializer.parse_message(session, message_json)

            x_message = {
                "@id": TestPackWireFormat.test_message_id,
                "~thread": {"thid": TestPackWireFormat.test_thread_id},
                "~transport": {"return_route": "all"},
                "content": "{}",
            }

            serializer.task_queue = None
            with mock.patch.object(
                serializer.v1pack_format, "unpack", mock.CoroutineMock()
            ) as mock_unpack:
                mock_unpack.return_value = "{missing-brace"
                with self.assertRaises(WireFormatParseError) as context:
                    await serializer.parse_message(session, json.dumps(x_message))
            assert "Message JSON parsing failed" in str(context.exception)

            serializer = PackWireFormat()
            serializer.task_queue = None
            with mock.patch.object(
                serializer.v1pack_format, "unpack", mock.CoroutineMock()
            ) as mock_unpack:
                mock_unpack.return_value = json.dumps([1, 2, 3])
                with self.assertRaises(WireFormatParseError) as context:
                    await serializer.parse_message(session, json.dumps(x_message))
            assert "Message JSON result is not an object" in str(context.exception)

            with self.assertRaises(WireFormatParseError):
                await serializer.unpack(session, "...", MessageReceipt())

    async def test_pack_x(self):
        serializer = PackWireFormat()

        async with self.profile.session() as session:
            with self.assertRaises(WireFormatEncodeError):
                await serializer.pack(session, None, [], [], "key")
            with self.assertRaises(WireFormatEncodeError):
                await serializer.pack(
                    session,
                    None,
                    ["key"],
                    None,
                    ["key"],
                )

        mock_wallet = mock.MagicMock(
            pack_message=mock.CoroutineMock(side_effect=WalletError())
        )
        self.profile.context.injector.bind_instance(BaseWallet, mock_wallet)
        async with self.profile.session() as session:
            with self.assertRaises(WireFormatEncodeError):
                await serializer.pack(session, None, ["key"], None, ["key"])

        mock_wallet = mock.MagicMock(
            pack_message=mock.CoroutineMock(
                side_effect=[json.dumps("message").encode("utf-8"), WalletError()]
            )
        )
        self.profile.context.injector.bind_instance(BaseWallet, mock_wallet)
        async with self.profile.session() as session:
            with mock.patch.object(
                test_module, "Forward", mock.MagicMock()
            ) as mock_forward:
                mock_forward.return_value = mock.MagicMock(to_json=mock.MagicMock())
                with self.assertRaises(WireFormatEncodeError):
                    await serializer.pack(session, None, ["key"], ["key"], ["key"])

    async def test_unpacked(self):
        serializer = PackWireFormat()
        message_json = json.dumps(self.test_message)
        async with self.profile.session() as session:
            message_dict, delivery = await serializer.parse_message(session, message_json)
            assert message_dict == self.test_message
            assert message_dict["@type"] == self.test_message_type
            assert delivery.thread_id == self.test_thread_id
            assert delivery.direct_response_mode == "all"

    async def test_fallback(self):
        serializer = PackWireFormat()

        message = self.test_message.copy()
        message.pop("@type")
        message_json = json.dumps(message)

        async with self.profile.session() as session:
            message_dict, delivery = await serializer.parse_message(session, message_json)
            assert delivery.raw_message == message_json
            assert message_dict == message

    async def test_encode_decode(self):
        async with self.profile.session() as session:
            wallet = session.inject(BaseWallet)
            local_did = await wallet.create_local_did(
                method=SOV, key_type=ED25519, seed=self.test_seed
            )
            serializer = PackWireFormat()
            recipient_keys = (local_did.verkey,)
            routing_keys = ()
            sender_key = local_did.verkey
            message_json = json.dumps(self.test_message)

            packed_json = await serializer.encode_message(
                session, message_json, recipient_keys, routing_keys, sender_key
            )
            packed = json.loads(packed_json)

            assert isinstance(packed, dict) and "protected" in packed
            assert serializer.get_recipient_keys(packed_json) == list(recipient_keys)
            with self.assertRaises(test_module.RecipientKeysError):
                serializer.get_recipient_keys(message_json)

            message_dict, delivery = await serializer.parse_message(session, packed_json)
            assert message_dict == self.test_message
            assert message_dict["@type"] == self.test_message_type
            assert delivery.thread_id == self.test_thread_id
            assert delivery.direct_response_mode == "all"

            plain_json = json.dumps("plain")
            assert (
                await serializer.encode_message(session, plain_json, None, None, None)
                == plain_json
            )

    async def test_forward(self):
        async with self.profile.session() as session:
            wallet = session.inject(BaseWallet)
            local_did = await wallet.create_local_did(
                method=SOV, key_type=ED25519, seed=self.test_seed
            )
            router_did = await wallet.create_local_did(
                method=SOV, key_type=ED25519, seed=self.test_routing_seed
            )
            serializer = PackWireFormat()
            recipient_keys = (local_did.verkey,)
            routing_keys = (router_did.verkey,)
            sender_key = local_did.verkey
            message_json = json.dumps(self.test_message)

            packed_json = await serializer.encode_message(
                session, message_json, recipient_keys, routing_keys, sender_key
            )
            packed = json.loads(packed_json)

            assert isinstance(packed, dict) and "protected" in packed

            message_dict, delivery = await serializer.parse_message(session, packed_json)
            assert message_dict["@type"] == DIDCommPrefix.qualify_current(FORWARD)
            assert delivery.recipient_verkey == router_did.verkey
            assert delivery.sender_verkey is None

    async def test_get_recipient_keys(self):
        recip_keys = ["kid1", "kid2", "kid3"]
        enc_message = {
            "protected": b64encode(
                json.dumps(
                    {"recipients": [{"header": {"kid": k}} for k in recip_keys]}
                ).encode("utf-8")
            ).decode()
        }

        serializer = PackWireFormat()
        actual_recip_keys = serializer.get_recipient_keys(json.dumps(enc_message))

        self.assertEqual(recip_keys, actual_recip_keys)

    async def test_get_recipient_keys_fails(self):
        enc_message = {"protected": {}}

        serializer = PackWireFormat()

        with self.assertRaises(RecipientKeysError):
            serializer.get_recipient_keys(json.dumps(enc_message))


class MockDIDCommMessaging(DIDCommMessaging):
    def __init__(
        self,
    ):
        crypto = mock.MagicMock()
        secrets = mock.MagicMock()
        resolver = mock.MagicMock()
        packaging = mock.AsyncMock()
        routing = mock.MagicMock()

        super().__init__(crypto, secrets, resolver, packaging, routing)


class TestV2PackWireFormat(IsolatedAsyncioTestCase):
    test_message = {
        "type": "test_message_type",
        "id": "test_message_id",
        "thid": "test_thread_id",
        "content": "test_content",
    }

    async def asyncSetUp(self):
        self.profile = await create_test_profile()
        self.profile.context.injector.bind_instance(DIDMethods, DIDMethods())
        self.profile.context.settings["experiment.didcomm_v2"] = True

    async def test_errors(self):
        wire_format = PackWireFormat()

        message = self.test_message.copy()
        message.pop("type")
        message_json = json.dumps(message)
        async with self.profile.session() as session:
            session.context.injector.bind_instance(
                DIDCommMessaging, MockDIDCommMessaging()
            )
            with self.assertRaises(WireFormatParseError) as context:
                await wire_format.parse_message(session, message_json)
            assert "Unable to determine appropriate WireFormat version" in str(
                context.exception
            )

            wire_format = V2PackWireFormat()
            bad_values = [None, "", "1", "[]", "{..."]

            for message_json in bad_values:
                with self.assertRaises(WireFormatParseError):
                    await wire_format.parse_message(session, message_json)

    async def test_fallback(self):
        serializer = V2PackWireFormat()

        test_dm = MockDIDCommMessaging()
        test_dm.packaging.unpack = mock.AsyncMock(side_effect=CryptoServiceError())
        async with self.profile.session() as session:
            session.context.injector.bind_instance(DIDCommMessaging, test_dm)

            message = self.test_message.copy()
            message.pop("type")
            message_json = json.dumps(message)

            message_dict, delivery = await serializer.parse_message(session, message_json)
            assert delivery.raw_message == message_json
            assert message_dict == message

    async def test_encode(self):
        serializer = V2PackWireFormat()

        test_dm = MockDIDCommMessaging()
        test_dm.pack = mock.AsyncMock(
            return_value=PackResult(
                message=self.test_message, target_services=mock.MagicMock()
            )
        )
        async with self.profile.session() as session:
            session.context.injector.bind_instance(DIDCommMessaging, test_dm)
            message = await serializer.encode_message(
                session=session,
                message_json=self.test_message,
                sender_key="sender_key",
                recipient_keys=["recip_key"],
                routing_keys=["route_key"],
            )

        assert message == self.test_message
