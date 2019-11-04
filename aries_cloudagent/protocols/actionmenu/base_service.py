"""Base action menu service classes."""

from abc import ABC, abstractmethod

from ...config.injection_context import InjectionContext
from ...connections.models.connection_record import ConnectionRecord
from ...messaging.agent_message import AgentMessage

from .messages.menu import Menu


class BaseMenuService(ABC):
    """Base action menu service interface."""

    def __init__(self, context: InjectionContext):
        """Initialize a menu service instance."""
        self._context = context

    @classmethod
    def service_handler(cls):
        """Quick accessor for conductor to use."""

        async def get_instance(context: InjectionContext):
            """Return registered server."""
            return cls(context)

        return get_instance

    @abstractmethod
    async def get_active_menu(
        self, connection: ConnectionRecord = None, thread_id: str = None
    ) -> Menu:
        """
        Render the current menu.

        Args:
            connection: The active connection record
            thread_id: The thread identifier from the requesting message.
        """

    @abstractmethod
    async def perform_menu_action(
        self,
        action_name: str,
        action_params: dict,
        connection: ConnectionRecord = None,
        thread_id: str = None,
    ) -> AgentMessage:
        """
        Perform an action defined by the active menu.

        Args:
            action_name: The unique name of the action being performed
            action_params: A collection of parameters for the action
            connection: The active connection record
            thread_id: The thread identifier from the requesting message.
        """
