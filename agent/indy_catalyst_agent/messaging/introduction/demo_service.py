"""Demo action menu service classes."""

import logging

from ..agent_message import AgentMessage
from .base_service import BaseMenuService
from .messages.menu import Menu
from .models.menu_form import MenuForm
from .models.menu_option import MenuOption
from .models.menu_form_param import MenuFormParam

LOGGER = logging.getLogger(__name__)


class DemoMenuService(BaseMenuService):
    """Demo action menu service."""

    async def get_active_menu(self) -> Menu:
        """Render the current menu."""
        search_form = MenuForm(
            title="Search introductions",
            description="Enter an attendee name below to perform a search.",
            submit_label="Search",
            params=(MenuFormParam(name="query", title="Attendee name", required=True),),
        )
        return Menu(
            title="Welcome to IIWBook",
            description="IIWBook facilitates connections between attendees by "
            + "verifying attendance and distributing connection invitations.",
            options=(
                MenuOption(
                    name="search-intros",
                    title="Search introductions",
                    description="Filter attendee records to make a connection",
                    form=search_form,
                ),
            ),
        )

    async def perform_menu_action(
        self, action_name: str, action_params: dict
    ) -> AgentMessage:
        """
        Perform an action defined by the active menu.

        Args:
            action_name: The unique name of the action being performed
            action_params: A collection of parameters for the action
            responder: The responder instance for sending a reply
        """

        intros = [
            {
                "name": "info;bob",
                "title": "Bob Terwilliger",
                "description": "The Krusty the Clown Show",
            },
            {"name": "info;ananse", "title": "Kwaku Ananse", "description": "Ghana"},
            {"name": "info;megatron", "title": "Megatron", "description": "Cybertron"},
        ]

        return_option = MenuOption(
            name="index", title="Back", description="Return to options"
        )

        if action_name == "index":
            return await self.get_active_menu()

        elif action_name == "search-intros":
            LOGGER.debug("search intros %s", action_params)
            query = action_params.get("query", "").lower()
            options = []
            for row in intros:
                if (
                    not query
                    or query in row["name"].lower()
                    or query in row["description"].lower()
                ):
                    options.append(MenuOption(**row))
            if not options:
                return Menu(
                    title="Search results",
                    description="No attendees were found matching your query.",
                    options=[return_option],
                )

            return Menu(
                title="Search results",
                description="The following attendees were found matching your query.",
                options=options,
            )

        elif action_name.startswith("info;"):
            for row in intros:
                if row["name"] == action_name:
                    request_form = MenuForm(
                        title="Request an introduction",
                        description="Ask to connect with this user.",
                        submit_label="Send Request",
                        params=(MenuFormParam(name="comments", title="Comments"),),
                    )
                    return Menu(
                        title=row["title"],
                        description=row["description"],
                        options=[
                            MenuOption(
                                name="request;" + action_name[5:],
                                title="Request an introduction",
                                description="Ask to connect with this user",
                                form=request_form,
                            ),
                            MenuOption(
                                name="index",
                                title="Back",
                                description="Return to options",
                            ),
                        ],
                    )

            return Menu(
                title="Attendee not found",
                description="The attendee could not be located.",
                options=[return_option],
            )

        elif action_name.startswith("request;"):
            LOGGER.info("requested intro to %s", action_name[8:])
            name = "info;" + action_name[8:]
            for row in intros:
                if row["name"] == name:

                    # send introduction proposal to user and ..

                    return Menu(
                        title="Request sent to {}".format(row["title"]),
                        description="""Your request for an introduction has been received,
                            and IIWBook will now ask the attendee for a connection
                            invitation. Once received by IIWBook this invitation will be
                            forwarded to your agent.""",
                        options=[
                            MenuOption(
                                name="index",
                                title="Done",
                                description="Return to options",
                            )
                        ],
                    )
