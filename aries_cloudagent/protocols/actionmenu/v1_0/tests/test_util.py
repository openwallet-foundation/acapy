from asynctest import TestCase as AsyncTestCase

from .....core.event_bus import EventBus, MockEventBus
from .....admin.request_context import AdminRequestContext

from .. import util as test_module
from ..models.menu_form_param import MenuFormParam
from ..models.menu_form import MenuForm
from ..models.menu_option import MenuOption


class TestActionMenuUtil(AsyncTestCase):
    async def test_save_retrieve_delete_connection_menu(self):
        context = AdminRequestContext.test_context()

        mock_event_bus = MockEventBus()
        context.profile.context.injector.bind_instance(EventBus, mock_event_bus)

        menu = test_module.Menu(
            title="title",
            description="description",
            errormsg=None,
            options=[
                MenuOption(
                    name=f"name-{i}",
                    title=f"option-title-{i}",
                    description=f"option-description-{i}",
                    disabled=bool(i % 2),
                    form=MenuForm(
                        title=f"form-title-{i}",
                        description=f"form-description-{i}",
                        params=[
                            MenuFormParam(
                                name=f"param-name-{i}-{j}",
                                title=f"param-title-{i}-{j}",
                                default=f"param-default-{i}-{j}",
                                description=f"param-description-{i}-{j}",
                                input_type="int",
                                required=bool((i + j) % 2),
                            )
                            for j in range(2)
                        ],
                    ),
                )
                for i in range(3)
            ],
        )
        connection_id = "connid"

        for i in range(2):  # once to add, once to update
            await test_module.save_connection_menu(menu, connection_id, context)

            assert len(mock_event_bus.events) == 1
            (_, event) = mock_event_bus.events[0]
            assert event.topic == "acapy::actionmenu::received"
            assert event.payload["connection_id"] == connection_id
            assert event.payload["menu"] == menu.serialize()
            mock_event_bus.events.clear()

        # retrieve connection menu
        assert (
            await test_module.retrieve_connection_menu(connection_id, context)
        ).serialize() == menu.serialize()

        # delete connection menu
        await test_module.save_connection_menu(None, connection_id, context)

        assert len(mock_event_bus.events) == 1
        (_, event) = mock_event_bus.events[0]
        assert event.topic == "acapy::actionmenu::received"
        assert event.payload == {"connection_id": connection_id, "menu": None}
        mock_event_bus.events.clear()

        # retrieve no menu
        assert (
            await test_module.retrieve_connection_menu(connection_id, context) is None
        )
