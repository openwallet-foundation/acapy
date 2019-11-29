"""Introduction service base classes."""

from abc import ABC, abstractmethod

from ...error import BaseError
from ...messaging.request_context import RequestContext

from .messages.invitation import Invitation


class IntroductionError(BaseError):
    """Generic introduction service error."""


class BaseIntroductionService(ABC):
    """Service handler for allowing connections to exchange invitations."""

    def __init__(self, context: RequestContext):
        """Init admin service."""
        self._context = context

    @classmethod
    def service_handler(cls):
        """Quick accessor for conductor to use."""

        async def get_instance(context: RequestContext):
            """Return registered server."""
            return cls(context)

        return get_instance

    @abstractmethod
    async def start_introduction(
        self,
        init_connection_id: str,
        target_connection_id: str,
        outbound_handler,
        message: str = None,
    ):
        """
        Start the introduction process between two connections.

        Args:
            init_connection_id: The connection initiating the request
            target_connection_id: The connection which is asked for an invitation
            outbound_handler: The outbound handler coroutine for sending a message
            message: The message to use when requesting the invitation
        """

    @abstractmethod
    async def return_invitation(
        self, target_connection_id: str, invitation: Invitation, outbound_handler
    ):
        """
        Handle the forwarding of an invitation to the responder.

        Args:
            target_connection_id: The ID of the connection sending the Invitation
            invitation: The received Invitation message
            outbound_handler: The outbound handler coroutine for sending a message
        """
