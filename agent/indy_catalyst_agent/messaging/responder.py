"""
A message responder.

The responder is provided to message handlers to enable them to send a new message
in response to the message being handled.
"""

from abc import ABC

from .agent_message import AgentMessage
from .connections.models.connection_target import ConnectionTarget
from ..error import BaseError


class ResponderError(BaseError):
    """Responder error."""

    pass


class BaseResponder(ABC):
    """Interface for message handlers to send responses."""

    async def send_outbound(self, message: AgentMessage, target: ConnectionTarget):
        """
        Send outbound message.

        Send a message to a given connection target (endpoint). The
        message may be queued for later delivery.

        Args:
            message: AgentMessage to be sent
            target: ConnectionTarget to send this message to
        """

    async def send_reply(self, message: AgentMessage):
        """
        Send message as reply.

        Send a message back to the same agent. This relies
        on the presence of an active connection. The message
        may be multicast to multiple endpoints or queued for
        later delivery.

        Args:
            message: AgentMessage to be sent
        """

    async def send_admin_message(self, message: AgentMessage):
        """
        Send admin message.

        Send an admin message to active listeners.

        Args:
            message: AgentMessage to be sent
        """
