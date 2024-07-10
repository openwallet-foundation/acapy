from unittest import IsolatedAsyncioTestCase

from aries_cloudagent.tests import mock

from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from .. import menu_handler as handler


class TestMenuHandler(IsolatedAsyncioTestCase):
    async def test_called(self):
        request_context = RequestContext.test_context()
        request_context.connection_record = mock.MagicMock()
        request_context.connection_record.connection_id = "dummy"
        request_context.connection_ready = True

        handler.save_connection_menu = mock.CoroutineMock()
        responder = MockResponder()

        request_context.message = handler.Menu()
        handler_inst = handler.MenuHandler()
        await handler_inst.handle(request_context, responder)

        handler.save_connection_menu.assert_called_once_with(
            request_context.message,
            request_context.connection_record.connection_id,
            request_context,
        )
