from unittest import IsolatedAsyncioTestCase

from .....messaging.request_context import RequestContext
from .....tests import mock
from .....utils.testing import create_test_profile
from .. import controller as test_module


class TestActionMenuController(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.profile = await create_test_profile()
        self.context = RequestContext(self.profile)

    async def test_controller(self):
        menu_service = mock.MagicMock(test_module.BaseMenuService, autospec=True)
        self.profile.context.injector.bind_instance(
            test_module.BaseMenuService, menu_service
        )

        controller = test_module.Controller("protocol")

        assert await controller.determine_roles(self.profile.context) == ["provider"]
