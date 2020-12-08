from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from .....core.in_memory import InMemoryProfile
from .....messaging.request_context import RequestContext
from .....messaging.responder import MockResponder

from .. import driver_service as test_module


class TestActionMenuService(AsyncTestCase):
    async def setUp(self):
        self.session = InMemoryProfile.test_session()
        self.context = RequestContext(self.session.profile)

    async def test_get_active_menu(self):
        self.responder = MockResponder()
        self.context.injector.bind_instance(test_module.BaseResponder, self.responder)

        self.menu_service = await (
            test_module.DriverMenuService.service_handler()(self.context)
        )

        connection = async_mock.MagicMock()
        connection.connection_id = "connid"
        thread_id = "thid"

        await self.menu_service.get_active_menu(connection, thread_id)

        webhooks = self.responder.webhooks
        assert len(webhooks) == 1
        (result, target) = webhooks[0]
        assert result == "get-active-menu"
        assert target == {
            "connection_id": connection.connection_id,
            "thread_id": thread_id,
        }

    async def test_perform_menu_action(self):
        self.responder = MockResponder()
        self.context.injector.bind_instance(test_module.BaseResponder, self.responder)

        self.menu_service = await (
            test_module.DriverMenuService.service_handler()(self.context)
        )

        action_name = "action"
        action_params = {"a": 1, "b": 2}
        connection = async_mock.MagicMock()
        connection.connection_id = "connid"
        thread_id = "thid"

        await self.menu_service.perform_menu_action(
            action_name, action_params, connection, thread_id
        )

        webhooks = self.responder.webhooks
        assert len(webhooks) == 1
        (result, target) = webhooks[0]
        assert result == "perform-menu-action"
        assert target == {
            "connection_id": connection.connection_id,
            "thread_id": thread_id,
            "action_name": action_name,
            "action_params": action_params,
        }
