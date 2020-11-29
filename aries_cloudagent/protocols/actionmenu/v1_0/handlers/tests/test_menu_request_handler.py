import pytest
from asynctest import (
    mock as async_mock,
    TestCase as AsyncTestCase,
)

from ......core.in_memory import InMemoryProfile
from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder

from .. import menu_request_handler as handler


class TestHandler(AsyncTestCase):
    async def setUp(self):
        self.session = InMemoryProfile.test_session()
        self.context = RequestContext(self.session.profile)

    async def test_called(self):
        MenuService = async_mock.MagicMock(handler.BaseMenuService, autospec=True)
        self.menu_service = MenuService()
        self.context.injector.bind_instance(handler.BaseMenuService, self.menu_service)
        self.context.inject = async_mock.CoroutineMock(return_value=self.menu_service)

        self.context.connection_record = async_mock.MagicMock()
        self.context.connection_record.connection_id = "dummy"

        responder = MockResponder()
        self.context.message = handler.MenuRequest()
        self.menu_service.get_active_menu = async_mock.CoroutineMock(
            return_value="menu"
        )

        handler_inst = handler.MenuRequestHandler()
        await handler_inst.handle(self.context, responder)

        messages = responder.messages
        assert len(messages) == 1
        (result, target) = messages[0]
        assert result == "menu"
        assert target == {}

    async def test_called_no_active_menu(self):
        MenuService = async_mock.MagicMock(handler.BaseMenuService, autospec=True)
        self.menu_service = MenuService()
        self.context.injector.bind_instance(handler.BaseMenuService, self.menu_service)
        self.context.inject = async_mock.CoroutineMock(return_value=self.menu_service)

        self.context.connection_record = async_mock.MagicMock()
        self.context.connection_record.connection_id = "dummy"

        responder = MockResponder()
        self.context.message = handler.MenuRequest()
        self.menu_service.get_active_menu = async_mock.CoroutineMock(return_value=None)

        handler_inst = handler.MenuRequestHandler()
        await handler_inst.handle(self.context, responder)

        messages = responder.messages
        assert not messages
