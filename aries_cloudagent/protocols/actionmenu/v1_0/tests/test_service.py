from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from .....core.event_bus import EventBus, MockEventBus
from .....core.in_memory import InMemoryProfile
from .....messaging.request_context import RequestContext

from .. import driver_service as test_module


class TestActionMenuService(AsyncTestCase):
    async def setUp(self):
        self.session = InMemoryProfile.test_session()
        self.context = RequestContext(self.session.profile)

    async def test_get_active_menu(self):
        mock_event_bus = MockEventBus()
        self.context.profile.context.injector.bind_instance(EventBus, mock_event_bus)

        self.menu_service = await test_module.DriverMenuService.service_handler()(
            self.context
        )

        connection = async_mock.MagicMock()
        connection.connection_id = "connid"
        thread_id = "thid"

        await self.menu_service.get_active_menu(
            self.context.profile, connection, thread_id
        )

        assert len(mock_event_bus.events) == 1
        (_, event) = mock_event_bus.events[0]
        assert event.topic == "acapy::actionmenu::get-active-menu"
        assert event.payload == {
            "connection_id": connection.connection_id,
            "thread_id": thread_id,
        }

    async def test_perform_menu_action(self):
        mock_event_bus = MockEventBus()
        self.context.profile.context.injector.bind_instance(EventBus, mock_event_bus)

        self.menu_service = await test_module.DriverMenuService.service_handler()(
            self.context
        )

        action_name = "action"
        action_params = {"a": 1, "b": 2}
        connection = async_mock.MagicMock()
        connection.connection_id = "connid"
        thread_id = "thid"

        await self.menu_service.perform_menu_action(
            self.context.profile,
            action_name,
            action_params,
            connection,
            thread_id,
        )

        assert len(mock_event_bus.events) == 1
        (_, event) = mock_event_bus.events[0]
        assert event.topic == "acapy::actionmenu::perform-menu-action"
        assert event.payload == {
            "connection_id": connection.connection_id,
            "thread_id": thread_id,
            "action_name": action_name,
            "action_params": action_params,
        }
