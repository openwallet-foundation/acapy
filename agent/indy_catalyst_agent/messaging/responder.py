from abc import ABC

from .agent_message import AgentMessage
from ..models.connection_target import ConnectionTarget
from ..error import BaseError


class ResponderError(BaseError):
    pass


class BaseResponder(ABC):
    """
    Interface for message handlers to send responses
    """

    async def send_outbound(self, message: AgentMessage, target: ConnectionTarget):
        """
        Send a message to a given connection target (endpoint). The
        message may be queued for later delivery.
        """

    async def send_reply(self, message: AgentMessage):
        """
        Send a message back to the same agent. This relies
        on the presence of an active connection. The message
        may be multicast to multiple endpoints or queued for
        later delivery.
        """

    async def send_admin_message(self, message: AgentMessage):
        """
        Send an admin message to active listeners.
        """
