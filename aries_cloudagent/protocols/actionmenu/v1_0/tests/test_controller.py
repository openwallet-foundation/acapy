from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from .....core.in_memory import InMemoryProfile
from .....messaging.request_context import RequestContext
from .. import controller as test_module


class TestActionMenuController(AsyncTestCase):
    async def setUp(self):
        self.session = InMemoryProfile.test_session()
        self.context = RequestContext(self.session.profile)

    async def test_controller(self):
        MenuService = async_mock.MagicMock(test_module.BaseMenuService, autospec=True)
        self.menu_service = MenuService()
        self.context.injector.bind_instance(
            test_module.BaseMenuService, self.menu_service
        )
        self.context.inject = async_mock.CoroutineMock(return_value=self.menu_service)

        controller = test_module.Controller("protocol")

        assert await controller.determine_roles(self.context) == ["provider"]
