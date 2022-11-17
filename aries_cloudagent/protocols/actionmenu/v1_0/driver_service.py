"""Driver-based action menu service classes."""

import logging

from ....connections.models.conn_record import ConnRecord
from ....core.profile import Profile
from ....messaging.agent_message import AgentMessage

from .base_service import BaseMenuService
from .messages.menu import Menu

LOGGER = logging.getLogger(__name__)


class DriverMenuService(BaseMenuService):
    """Driver-based action menu service."""

    async def get_active_menu(
        self,
        profile: Profile,
        connection: ConnRecord = None,
        thread_id: str = None,
    ) -> Menu:
        """
        Render the current menu.

        Args:
            profile: The profile
            connection: The active connection record
            thread_id: The thread identifier from the requesting message.
        """
        await profile.notify(
            "acapy::actionmenu::get-active-menu",
            {
                "connection_id": connection and connection.connection_id,
                "thread_id": thread_id,
            },
        )
        return None

    async def perform_menu_action(
        self,
        profile: Profile,
        action_name: str,
        action_params: dict,
        connection: ConnRecord = None,
        thread_id: str = None,
    ) -> AgentMessage:
        """
        Perform an action defined by the active menu.

        Args:
            profile: The profile
            action_name: The unique name of the action being performed
            action_params: A collection of parameters for the action
            connection: The active connection record
            thread_id: The thread identifier from the requesting message.
        """
        await profile.notify(
            "acapy::actionmenu::perform-menu-action",
            {
                "connection_id": connection and connection.connection_id,
                "thread_id": thread_id,
                "action_name": action_name,
                "action_params": action_params,
            },
        )
        return None
