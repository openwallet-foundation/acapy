import pytest

from asynctest import mock as async_mock, TestCase as AsyncTestCase

from ......core.oob_processor import OobMessageProcessor
from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......transport.inbound.receipt import MessageReceipt

from ...messages.pres import V20Pres

from .. import pres_handler as test_module


class TestV20PresHandler(AsyncTestCase):
    async def test_called(self):
        request_context = RequestContext.test_context()
        request_context.message_receipt = MessageReceipt()
        request_context.settings["debug.auto_verify_presentation"] = False

        oob_record = async_mock.MagicMock()
        mock_oob_processor = async_mock.MagicMock(
            find_oob_record_for_inbound_message=async_mock.CoroutineMock(
                return_value=oob_record
            )
        )
        request_context.injector.bind_instance(OobMessageProcessor, mock_oob_processor)

        with async_mock.patch.object(
            test_module, "V20PresManager", autospec=True
        ) as mock_pres_mgr:
            mock_pres_mgr.return_value.receive_pres = async_mock.CoroutineMock()
            request_context.message = V20Pres()
            request_context.connection_ready = True
            request_context.connection_record = async_mock.MagicMock()
            handler = test_module.V20PresHandler()
            responder = MockResponder()
            await handler.handle(request_context, responder)

        mock_pres_mgr.assert_called_once_with(request_context.profile)
        mock_pres_mgr.return_value.receive_pres.assert_called_once_with(
            request_context.message, request_context.connection_record, oob_record
        )
        assert not responder.messages

    async def test_called_auto_verify(self):
        request_context = RequestContext.test_context()
        request_context.message_receipt = MessageReceipt()
        request_context.settings["debug.auto_verify_presentation"] = True

        oob_record = async_mock.MagicMock()
        mock_oob_processor = async_mock.MagicMock(
            find_oob_record_for_inbound_message=async_mock.CoroutineMock(
                return_value=oob_record
            )
        )
        request_context.injector.bind_instance(OobMessageProcessor, mock_oob_processor)

        with async_mock.patch.object(
            test_module, "V20PresManager", autospec=True
        ) as mock_pres_mgr:
            mock_pres_mgr.return_value.receive_pres = async_mock.CoroutineMock()
            mock_pres_mgr.return_value.verify_pres = async_mock.CoroutineMock()
            request_context.message = V20Pres()
            request_context.connection_ready = True
            request_context.connection_record = async_mock.MagicMock()
            handler = test_module.V20PresHandler()
            responder = MockResponder()
            await handler.handle(request_context, responder)

        mock_pres_mgr.assert_called_once_with(request_context.profile)
        mock_pres_mgr.return_value.receive_pres.assert_called_once_with(
            request_context.message, request_context.connection_record, oob_record
        )
        assert not responder.messages

    async def test_called_auto_verify_x(self):
        request_context = RequestContext.test_context()
        request_context.message_receipt = MessageReceipt()
        request_context.settings["debug.auto_verify_presentation"] = True

        oob_record = async_mock.MagicMock()
        mock_oob_processor = async_mock.MagicMock(
            find_oob_record_for_inbound_message=async_mock.CoroutineMock(
                return_value=oob_record
            )
        )
        request_context.injector.bind_instance(OobMessageProcessor, mock_oob_processor)

        with async_mock.patch.object(
            test_module, "V20PresManager", autospec=True
        ) as mock_pres_mgr:
            mock_pres_mgr.return_value = async_mock.MagicMock(
                receive_pres=async_mock.CoroutineMock(
                    return_value=async_mock.MagicMock(
                        save_error_state=async_mock.CoroutineMock()
                    )
                ),
                verify_pres=async_mock.CoroutineMock(
                    side_effect=test_module.LedgerError()
                ),
            )

            request_context.message = V20Pres()
            request_context.connection_ready = True
            request_context.connection_record = async_mock.MagicMock()
            handler = test_module.V20PresHandler()
            responder = MockResponder()

            with async_mock.patch.object(
                handler._logger, "exception", async_mock.MagicMock()
            ) as mock_log_exc:
                await handler.handle(request_context, responder)
                mock_log_exc.assert_called_once()
