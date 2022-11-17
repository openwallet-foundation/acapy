"""Introduction service base classes."""

from abc import ABC, abstractmethod

from ....core.error import BaseError
from ....core.profile import ProfileSession

from .messages.invitation import Invitation


class IntroductionError(BaseError):
    """Generic introduction service error."""


class BaseIntroductionService(ABC):
    """Service handler for allowing connections to exchange invitations."""

    def __init__(self):
        """Init admin service."""

    @classmethod
    def service_handler(cls):
        """Quick accessor for conductor to use."""

        async def get_instance():
            """Return registered server."""
            return cls()

        return get_instance

    @abstractmethod
    async def start_introduction(
        self,
        init_connection_id: str,
        target_connection_id: str,
        outbound_handler,
        session: ProfileSession,
        message: str = None,
    ):
        """
        Start the introduction process between two connections.

        Args:
            init_connection_id: The connection initiating the request
            target_connection_id: The connection which is asked for an invitation
            outbound_handler: The outbound handler coroutine for sending a message
            session: Profile session to use for connection, introduction records
            message: The message to use when requesting the invitation
        """

    @abstractmethod
    async def return_invitation(
        self,
        target_connection_id: str,
        invitation: Invitation,
        session: ProfileSession,
        outbound_handler,
    ):
        """
        Handle the forwarding of an invitation to the responder.

        Args:
            target_connection_id: The ID of the connection sending the Invitation
            invitation: The received Invitation message
            session: Profile session to use for introduction records
            outbound_handler: The outbound handler coroutine for sending a message
        """
