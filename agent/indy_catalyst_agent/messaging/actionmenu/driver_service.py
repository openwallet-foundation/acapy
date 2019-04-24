"""Driver-based action menu service classes."""

import asyncio
import logging

from ..agent_message import AgentMessage
from .base_service import BaseMenuService
from .messages.menu import Menu
from ..util import send_webhook

LOGGER = logging.getLogger(__name__)


class DriverMenuService(BaseMenuService):
    """Driver-based action menu service."""

    async def get_active_menu(self, thread_id: str = None) -> Menu:
        """
        Render the current menu.

        Args:
            thread_id: The thread identifier from the requesting message.
        """
        asyncio.ensure_future(
            send_webhook(
                "get-active-menu",
                {
                    "connection_id": self._context.connection_record.connection_id,
                    "thread_id": thread_id,
                },
            )
        )
        return None

    async def perform_menu_action(
        self, action_name: str, action_params: dict, thread_id: str = None
    ) -> AgentMessage:
        """
        Perform an action defined by the active menu.

        Args:
            action_name: The unique name of the action being performed
            action_params: A collection of parameters for the action
            thread_id: The thread identifier from the requesting message.
        """
        asyncio.ensure_future(
            send_webhook(
                "perform-menu-action",
                {
                    "connection_id": self._context.connection_record.connection_id,
                    "thread_id": thread_id,
                    "action_name": action_name,
                    "action_params": action_params,
                },
            )
        )
        return None
