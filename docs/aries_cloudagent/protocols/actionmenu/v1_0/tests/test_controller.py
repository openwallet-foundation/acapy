from unittest import IsolatedAsyncioTestCase
from aries_cloudagent.tests import mock

from .....core.in_memory import InMemoryProfile
from .....messaging.request_context import RequestContext
from .. import controller as test_module


class TestActionMenuController(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.session = InMemoryProfile.test_session()
        self.context = RequestContext(self.session.profile)

    async def test_controller(self):
        MenuService = mock.MagicMock(test_module.BaseMenuService, autospec=True)
        self.menu_service = MenuService()
        self.context.injector.bind_instance(
            test_module.BaseMenuService, self.menu_service
        )
        self.context.inject = mock.CoroutineMock(return_value=self.menu_service)

        controller = test_module.Controller("protocol")

        assert await controller.determine_roles(self.context) == ["provider"]
