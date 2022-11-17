from asynctest import mock as async_mock, TestCase as AsyncTestCase

from ......core.oob_processor import OobMessageProcessor
from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......transport.inbound.receipt import MessageReceipt

from ...messages.pres_ack import V20PresAck

from .. import pres_ack_handler as test_module


class TestV20PresAckHandler(AsyncTestCase):
    async def test_called(self):
        request_context = RequestContext.test_context()
        request_context.message_receipt = MessageReceipt()
        session = request_context.session()

        mock_oob_processor = async_mock.MagicMock(
            find_oob_record_for_inbound_message=async_mock.CoroutineMock(
                return_value=async_mock.MagicMock()
            )
        )
        request_context.injector.bind_instance(OobMessageProcessor, mock_oob_processor)

        with async_mock.patch.object(
            test_module, "V20PresManager", autospec=True
        ) as mock_pres_mgr:
            mock_pres_mgr.return_value.receive_pres_ack = async_mock.CoroutineMock()
            request_context.message = V20PresAck()
            request_context.connection_ready = True
            request_context.connection_record = async_mock.MagicMock()
            handler = test_module.V20PresAckHandler()
            responder = MockResponder()
            await handler.handle(request_context, responder)

        mock_pres_mgr.assert_called_once_with(request_context.profile)
        mock_pres_mgr.return_value.receive_pres_ack.assert_called_once_with(
            request_context.message, request_context.connection_record
        )
        assert not responder.messages

    async def test_called_not_ready(self):
        request_context = RequestContext.test_context()
        request_context.message_receipt = MessageReceipt()
        request_context.connection_record = async_mock.MagicMock()

        with async_mock.patch.object(
            test_module, "V20PresManager", autospec=True
        ) as mock_pres_mgr:
            mock_pres_mgr.return_value.receive_pres_ack = async_mock.CoroutineMock()
            request_context.message = V20PresAck()
            request_context.connection_ready = False
            handler = test_module.V20PresAckHandler()
            responder = MockResponder()
            with self.assertRaises(test_module.HandlerException) as err:
                await handler.handle(request_context, responder)
        assert err.exception.message == "Connection used for presentation ack not ready"

        assert not responder.messages

    async def test_called_no_connection_no_oob(self):
        request_context = RequestContext.test_context()
        request_context.message_receipt = MessageReceipt()

        mock_oob_processor = async_mock.MagicMock(
            find_oob_record_for_inbound_message=async_mock.CoroutineMock(
                # No oob record found
                return_value=None
            )
        )
        request_context.injector.bind_instance(OobMessageProcessor, mock_oob_processor)

        request_context.message = V20PresAck()
        handler = test_module.V20PresAckHandler()
        responder = MockResponder()
        with self.assertRaises(test_module.HandlerException) as err:
            await handler.handle(request_context, responder)
        assert (
            err.exception.message
            == "No connection or associated connectionless exchange found for presentation ack"
        )

        assert not responder.messages
