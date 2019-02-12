from abc import ABC

from .agent_message import AgentMessage
from ..connection import Connection
from ..error import BaseError


class ResponderError(BaseError):
    pass


class BaseResponder(ABC):
    """
    Interface for message handlers to send responses
    """

    async def send_outbound(self, connection: Connection, message: AgentMessage):
        """
        Send a message to a given connection (endpoint). The
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
