import asyncio
import pytest

from asynctest import TestCase, mock as async_mock

from ....admin.server import AdminResponder
from ....core.in_memory import InMemoryProfile
from ....messaging.responder import BaseResponder
from ....multitenant.base import BaseMultitenantManager
from ....multitenant.manager import MultitenantManager

from ...error import WireFormatError
from ...outbound.message import OutboundMessage

from ..message import InboundMessage
from ..receipt import MessageReceipt
from ..session import InboundSession


class TestInboundSession(TestCase):
    def setUp(self):
        self.profile = InMemoryProfile.test_profile()

    def test_init(self):
        test_inbound = async_mock.MagicMock()
        test_session_id = "session-id"
        test_wire_format = async_mock.MagicMock()
        test_client_info = {"client": "info"}
        test_close = async_mock.MagicMock()
        test_reply_mode = MessageReceipt.REPLY_MODE_ALL
        test_reply_thread_ids = {"1", "2"}
        test_reply_verkeys = {"3", "4"}
        test_transport_type = "transport-type"
        sess = InboundSession(
            profile=self.profile,
            inbound_handler=test_inbound,
            session_id=test_session_id,
            wire_format=test_wire_format,
            client_info=test_client_info,
            close_handler=test_close,
            reply_mode=test_reply_mode,
            reply_thread_ids=test_reply_thread_ids,
            reply_verkeys=test_reply_verkeys,
            transport_type=test_transport_type,
        )

        assert sess.profile is self.profile
        assert sess.session_id == test_session_id
        assert sess.wire_format is test_wire_format
        assert sess.client_info == test_client_info
        assert sess.reply_mode == test_reply_mode
        assert sess.transport_type == test_transport_type
        assert "1" in sess.reply_thread_ids
        assert "3" in sess.reply_verkeys

        test_msg = async_mock.MagicMock()
        with async_mock.patch.object(sess, "process_inbound") as process:
            sess.receive_inbound(test_msg)
            process.assert_called_once_with(test_msg)
            test_inbound.assert_called_once_with(
                sess.profile, test_msg, can_respond=False
            )

        sess.close()
        test_close.assert_called_once()
        assert sess.closed

    def test_setters(self):
        sess = InboundSession(
            profile=self.profile,
            inbound_handler=None,
            session_id=None,
            wire_format=None,
        )

        sess.reply_mode = MessageReceipt.REPLY_MODE_ALL
        assert sess.reply_mode == MessageReceipt.REPLY_MODE_ALL

        sess.add_reply_thread_ids("1")
        assert "1" in sess.reply_thread_ids
        sess.add_reply_verkeys("2")
        assert "2" in sess.reply_verkeys

        sess.reply_mode = "invalid"
        assert not sess.reply_mode
        assert not sess.reply_thread_ids  # reset by setter method

    async def test_parse_inbound(self):
        test_session_id = "session-id"
        test_transport_type = "transport-type"
        test_wire_format = async_mock.MagicMock()
        test_wire_format.parse_message = async_mock.CoroutineMock()
        test_parsed = "parsed-payload"
        test_receipt = async_mock.MagicMock()
        test_wire_format.parse_message.return_value = (test_parsed, test_receipt)
        sess = InboundSession(
            profile=self.profile,
            inbound_handler=None,
            session_id=test_session_id,
            wire_format=test_wire_format,
            transport_type=test_transport_type,
        )

        session = self.profile.session()
        setattr(self.profile, "session", async_mock.MagicMock(return_value=session))

        test_payload = "{}"
        result = await sess.parse_inbound(test_payload)
        test_wire_format.parse_message.assert_awaited_once_with(session, test_payload)
        assert result.payload == test_parsed
        assert result.receipt is test_receipt
        assert result.session_id == test_session_id
        assert result.transport_type == test_transport_type

    async def test_receive(self):
        self.multitenant_mgr = async_mock.MagicMock(MultitenantManager, autospec=True)
        self.multitenant_mgr.get_wallets_by_message = async_mock.CoroutineMock(
            return_value=[async_mock.MagicMock(is_managed=True)]
        )
        self.multitenant_mgr.get_wallet_profile = async_mock.CoroutineMock(
            return_value=self.profile
        )
        self.profile.context.injector.bind_instance(
            BaseMultitenantManager, self.multitenant_mgr
        )
        self.profile.context.update_settings({"multitenant.enabled": True})
        self.base_responder = async_mock.MagicMock(AdminResponder, autospec=True)
        self.profile.context.injector.bind_instance(BaseResponder, self.base_responder)

        sess = InboundSession(
            profile=self.profile,
            inbound_handler=None,
            session_id=None,
            wire_format=None,
        )
        test_msg = async_mock.MagicMock()

        with async_mock.patch.object(
            sess, "parse_inbound", async_mock.CoroutineMock()
        ) as encode, async_mock.patch.object(
            sess, "receive_inbound", async_mock.MagicMock()
        ) as receive:
            result = await sess.receive(test_msg)
            encode.assert_awaited_once_with(test_msg)
            receive.assert_called_once_with(encode.return_value)
            assert result is encode.return_value

    async def test_receive_no_wallet_found(self):
        self.multitenant_mgr = async_mock.MagicMock(MultitenantManager, autospec=True)
        self.multitenant_mgr.get_wallets_by_message = async_mock.CoroutineMock(
            side_effect=ValueError("no such wallet")
        )
        self.multitenant_mgr.get_wallet_profile = async_mock.CoroutineMock(
            return_value=self.profile
        )
        self.profile.context.injector.bind_instance(
            BaseMultitenantManager, self.multitenant_mgr
        )
        self.profile.context.update_settings({"multitenant.enabled": True})

        sess = InboundSession(
            profile=self.profile,
            inbound_handler=None,
            session_id=None,
            wire_format=None,
        )
        test_msg = async_mock.MagicMock()

        with async_mock.patch.object(
            sess, "parse_inbound", async_mock.CoroutineMock()
        ) as encode, async_mock.patch.object(
            sess, "receive_inbound", async_mock.MagicMock()
        ) as receive:
            result = await sess.receive(test_msg)
            encode.assert_awaited_once_with(test_msg)
            receive.assert_called_once_with(encode.return_value)
            assert result is encode.return_value

    def test_process_inbound(self):
        test_session_id = "session-id"
        test_thread_id = "thread-id"
        test_verkey = "verkey"
        sess = InboundSession(
            profile=self.profile,
            inbound_handler=None,
            session_id=test_session_id,
            wire_format=None,
        )

        receipt = MessageReceipt(
            direct_response_mode=MessageReceipt.REPLY_MODE_THREAD,
            thread_id=test_thread_id,
            sender_verkey=test_verkey,
        )

        receipt.recipient_did = "dummy"
        assert receipt.recipient_did == "dummy"
        receipt.recipient_did_public = True
        assert receipt.recipient_did_public
        receipt.recipient_did = None
        receipt.recipient_did_public = None
        assert receipt.recipient_did is None
        assert receipt.recipient_did_public is None
        receipt.sender_did = "dummy"
        assert receipt.sender_did == "dummy"
        receipt.sender_did = None
        assert receipt.sender_did is None
        assert "direct_response_mode" in str(receipt)

        message = InboundMessage(payload=None, receipt=receipt)
        sess.process_inbound(message)
        assert sess.reply_mode == receipt.direct_response_mode
        assert test_verkey in sess.reply_verkeys
        assert test_thread_id in sess.reply_thread_ids

        assert receipt.in_time is None
        receipt.connection_id = "dummy"
        assert receipt.connection_id == "dummy"

    def test_select_outbound(self):
        test_session_id = "session-id"
        test_thread_id = "thread-id"
        test_verkey = "verkey"
        sess = InboundSession(
            profile=self.profile,
            inbound_handler=None,
            session_id=test_session_id,
            wire_format=None,
        )

        sess.reply_mode = MessageReceipt.REPLY_MODE_ALL
        test_msg = OutboundMessage(payload=None)
        assert not sess.select_outbound(test_msg)  # no key
        test_msg.reply_session_id = test_session_id
        assert not sess.select_outbound(test_msg)  # no difference
        sess.can_respond = True
        assert not sess.select_outbound(test_msg)  # no difference
        test_msg.reply_to_verkey = test_verkey
        sess.add_reply_verkeys(test_verkey)
        assert sess.select_outbound(test_msg)

        sess.reply_mode = MessageReceipt.REPLY_MODE_THREAD
        sess.reply_verkeys = None
        sess.reply_thread_ids = None
        test_msg = OutboundMessage(payload=None)
        assert not sess.select_outbound(test_msg)
        sess.add_reply_thread_ids(test_thread_id)
        test_msg.reply_thread_id = test_thread_id
        assert not sess.select_outbound(test_msg)
        sess.add_reply_verkeys(test_verkey)
        test_msg.reply_to_verkey = test_verkey
        assert sess.select_outbound(test_msg)

        sess.close()
        assert not sess.select_outbound(test_msg)

    async def test_wait_response(self):
        sess = InboundSession(
            profile=self.profile,
            inbound_handler=None,
            session_id=None,
            wire_format=None,
        )
        test_msg = OutboundMessage(payload=None)
        sess.set_response(test_msg)
        assert sess.response_event.is_set()
        assert sess.response_buffered

        with async_mock.patch.object(
            sess, "encode_outbound", async_mock.CoroutineMock()
        ) as encode:
            result = await asyncio.wait_for(sess.wait_response(), 0.1)
            assert encode.awaited_once_with(test_msg)
            assert result is encode.return_value

        sess.clear_response()
        assert not sess.response_buffer

        sess.close()
        assert await asyncio.wait_for(sess.wait_response(), 0.1) is None

    async def test_wait_response_x(self):
        sess = InboundSession(
            profile=self.profile,
            inbound_handler=None,
            session_id=None,
            wire_format=None,
        )
        test_msg = OutboundMessage(payload=None)
        sess.set_response(test_msg)
        assert sess.response_event.is_set()
        assert sess.response_buffered

        with async_mock.patch.object(
            sess, "encode_outbound", async_mock.CoroutineMock()
        ) as encode:
            encode.side_effect = WireFormatError()
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(sess.wait_response(), 0.1)

        assert not sess.response_buffer

        sess.close()
        assert await asyncio.wait_for(sess.wait_response(), 0.1) is None

    async def test_encode_response(self):
        test_wire_format = async_mock.MagicMock()
        test_wire_format.encode_message = async_mock.CoroutineMock()
        sess = InboundSession(
            profile=self.profile,
            inbound_handler=None,
            session_id=None,
            wire_format=test_wire_format,
        )
        test_msg = OutboundMessage(payload=None)
        test_from_verkey = "from-verkey"
        test_to_verkey = "to-verkey"

        session = self.profile.session()
        setattr(self.profile, "session", async_mock.MagicMock(return_value=session))

        with self.assertRaises(WireFormatError):
            await sess.encode_outbound(test_msg)
        test_msg.payload = "{}"
        with self.assertRaises(WireFormatError):
            await sess.encode_outbound(test_msg)
        test_msg.reply_from_verkey = test_from_verkey
        test_msg.reply_to_verkey = test_to_verkey
        result = await sess.encode_outbound(test_msg)
        assert result is test_wire_format.encode_message.return_value

        test_wire_format.encode_message.assert_awaited_once_with(
            session,
            test_msg.payload,
            [test_to_verkey],
            None,
            test_from_verkey,
        )

    async def test_accept_response(self):
        sess = InboundSession(
            profile=self.profile,
            inbound_handler=None,
            session_id=None,
            wire_format=None,
        )
        test_msg = OutboundMessage(payload=None)

        with async_mock.patch.object(sess, "select_outbound") as selector:
            selector.return_value = False

            accepted = sess.accept_response(test_msg)
            assert not accepted and not accepted.retry

            sess.set_response(OutboundMessage(payload=None))
            selector.return_value = True
            accepted = sess.accept_response(test_msg)
            assert not accepted and accepted.retry

            sess.clear_response()
            accepted = sess.accept_response(test_msg)
            assert accepted

    async def test_context_mgr(self):
        sess = InboundSession(
            profile=self.profile,
            inbound_handler=None,
            session_id=None,
            wire_format=None,
        )
        assert not sess.closed
        async with sess:
            pass
        assert sess.closed
