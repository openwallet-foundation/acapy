from unittest import IsolatedAsyncioTestCase

from ......core.oob_processor import OobMessageProcessor
from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......tests import mock
from ......transport.inbound.receipt import MessageReceipt
from ......utils.testing import create_test_profile
from ...messages.presentation import Presentation
from .. import presentation_handler as test_module


class TestPresentationHandler(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.profile = await create_test_profile()
        self.request_context = RequestContext.test_context(self.profile)
        self.request_context.message_receipt = MessageReceipt()
        self.request_context.settings["debug.auto_verify_presentation"] = False

        self.oob_record = mock.MagicMock()
        mock_oob_processor = mock.MagicMock(OobMessageProcessor, autospec=True)
        mock_oob_processor.find_oob_record_for_inbound_message = mock.CoroutineMock(
            return_value=self.oob_record
        )
        self.request_context.injector.bind_instance(
            OobMessageProcessor, mock_oob_processor
        )

    async def test_called(self):
        with mock.patch.object(
            test_module, "PresentationManager", autospec=True
        ) as mock_pres_mgr:
            mock_pres_mgr.return_value.receive_presentation = mock.CoroutineMock()
            self.request_context.message = Presentation()
            self.request_context.connection_ready = True
            self.request_context.connection_record = mock.MagicMock()
            handler = test_module.PresentationHandler()
            responder = MockResponder()
            await handler.handle(self.request_context, responder)

        mock_pres_mgr.assert_called_once_with(self.request_context.profile)
        mock_pres_mgr.return_value.receive_presentation.assert_called_once_with(
            self.request_context.message,
            self.request_context.connection_record,
            self.oob_record,
        )
        assert not responder.messages

    async def test_called_auto_verify(self):
        with mock.patch.object(
            test_module, "PresentationManager", autospec=True
        ) as mock_pres_mgr:
            mock_pres_mgr.return_value.receive_presentation = mock.CoroutineMock()
            mock_pres_mgr.return_value.verify_presentation = mock.CoroutineMock()
            self.request_context.message = Presentation()
            self.request_context.connection_ready = True
            self.request_context.connection_record = mock.MagicMock()
            handler = test_module.PresentationHandler()
            responder = MockResponder()
            await handler.handle(self.request_context, responder)

        mock_pres_mgr.assert_called_once_with(self.request_context.profile)
        mock_pres_mgr.return_value.receive_presentation.assert_called_once_with(
            self.request_context.message,
            self.request_context.connection_record,
            self.oob_record,
        )
        assert not responder.messages

    async def test_called_auto_verify_x(self):
        with mock.patch.object(
            test_module, "PresentationManager", autospec=True
        ) as mock_pres_mgr:
            mock_pres_mgr.return_value = mock.MagicMock(
                receive_presentation=mock.CoroutineMock(
                    return_value=mock.MagicMock(save_error_state=mock.CoroutineMock())
                ),
                verify_presentation=mock.CoroutineMock(
                    side_effect=test_module.LedgerError()
                ),
            )

            self.request_context.message = Presentation()
            self.request_context.connection_ready = True
            self.request_context.connection_record = mock.MagicMock()
            handler = test_module.PresentationHandler()
            responder = MockResponder()

            with mock.patch.object(
                handler._logger, "exception", mock.MagicMock()
            ) as mock_log_exc:
                await handler.handle(self.request_context, responder)
                mock_log_exc.assert_called_once()
