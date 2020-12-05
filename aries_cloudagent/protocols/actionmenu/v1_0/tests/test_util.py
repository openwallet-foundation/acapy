from asynctest import TestCase as AsyncTestCase

from aries_cloudagent.core.in_memory import InMemoryProfile
from aries_cloudagent.messaging.responder import MockResponder
from aries_cloudagent.storage.base import BaseStorage
from aries_cloudagent.wallet.base import BaseWallet

from .. import util as test_module
from ..models.menu_form_param import MenuFormParam
from ..models.menu_form import MenuForm
from ..models.menu_option import MenuOption


class TestUtil(AsyncTestCase):
    async def test_save_retrieve_delete_connection_menu(self):
        session = InMemoryProfile.test_session()

        responder = MockResponder()
        session.context.injector.bind_instance(test_module.BaseResponder, responder)

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
            await test_module.save_connection_menu(menu, connection_id, session)

            webhooks = responder.webhooks
            assert len(webhooks) == 1
            (result, target) = webhooks[0]
            assert result == "actionmenu"
            assert target["connection_id"] == connection_id
            assert target["menu"] == menu.serialize()
            responder.webhooks.clear()

        # retrieve connection menu
        assert (
            await test_module.retrieve_connection_menu(connection_id, session)
        ).serialize() == menu.serialize()

        # delete connection menu
        await test_module.save_connection_menu(None, connection_id, session)

        webhooks = responder.webhooks
        assert len(webhooks) == 1
        (result, target) = webhooks[0]
        assert result == "actionmenu"
        assert target == {"connection_id": connection_id, "menu": None}
        responder.webhooks.clear()

        # retrieve no menu
        assert (
            await test_module.retrieve_connection_menu(connection_id, session) is None
        )
