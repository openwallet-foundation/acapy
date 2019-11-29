from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from ....config.injection_context import InjectionContext
from ....messaging.request_context import RequestContext
from .. import controller as test_module


class TestActionMenuController(AsyncTestCase):
    async def test_controller(self):
        self.context = RequestContext(
            base_context=InjectionContext(enforce_typing=False)
        )
        MenuService = async_mock.MagicMock(test_module.BaseMenuService, autospec=True)
        self.menu_service = MenuService()
        self.context.injector.bind_instance(
            test_module.BaseMenuService,
            self.menu_service
        )
        self.context.inject = async_mock.CoroutineMock(
            return_value=self.menu_service
        )

        controller = test_module.Controller("protocol")

        assert await controller.determine_roles(self.context) == ["provider"]
