import pytest
from asynctest import (
    mock as async_mock,
    TestCase as AsyncTestCase,
)

from .....config.injection_context import InjectionContext
from .....messaging.request_context import RequestContext
from .....messaging.responder import MockResponder

from .. import menu_request_handler as handler


class TestHandler(AsyncTestCase):
    async def test_called(self):
        self.context = RequestContext(
            base_context=InjectionContext(enforce_typing=False)
        )
        MenuService = async_mock.MagicMock(handler.BaseMenuService, autospec=True)
        self.menu_service = MenuService()
        self.context.injector.bind_instance(handler.BaseMenuService, self.menu_service)
        self.context.inject = async_mock.CoroutineMock(
            return_value=self.menu_service
        )

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
        self.context = RequestContext(
            base_context=InjectionContext(enforce_typing=False)
        )
        MenuService = async_mock.MagicMock(handler.BaseMenuService, autospec=True)
        self.menu_service = MenuService()
        self.context.injector.bind_instance(handler.BaseMenuService, self.menu_service)
        self.context.inject = async_mock.CoroutineMock(
            return_value=self.menu_service
        )

        self.context.connection_record = async_mock.MagicMock()
        self.context.connection_record.connection_id = "dummy"

        responder = MockResponder()
        self.context.message = handler.MenuRequest()
        self.menu_service.get_active_menu = async_mock.CoroutineMock(
            return_value=None
        )

        handler_inst = handler.MenuRequestHandler()
        await handler_inst.handle(self.context, responder)

        messages = responder.messages
        assert not messages
