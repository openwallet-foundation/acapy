"""Represents a forwarded invitation from another agent."""

from marshmallow import fields

from .....messaging.agent_message import AgentMessage, AgentMessageSchema
from .....protocols.connections.v1_0.messages.connection_invitation import (
    ConnectionInvitation,
    ConnectionInvitationSchema,
)
from ..message_types import FORWARD_INVITATION, PROTOCOL_PACKAGE

HANDLER_CLASS = (
    f"{PROTOCOL_PACKAGE}.handlers.forward_invitation_handler.ForwardInvitationHandler"
)


class ForwardInvitation(AgentMessage):
    """Class representing an invitation to be forwarded."""

    class Meta:
        """Metadata for a forwarded invitation."""

        handler_class = HANDLER_CLASS
        message_type = FORWARD_INVITATION
        schema_class = "ForwardInvitationSchema"

    def __init__(
        self, *, invitation: ConnectionInvitation = None, message: str = None, **kwargs
    ):
        """
        Initialize invitation object.

        Args:
            invitation: The connection invitation
            message: Comments on the introduction
        """
        super().__init__(**kwargs)
        self.invitation = invitation
        self.message = message


class ForwardInvitationSchema(AgentMessageSchema):
    """ForwardInvitation request schema class."""

    class Meta:
        """ForwardInvitation request schema metadata."""

        model_class = ForwardInvitation

    invitation = fields.Nested(ConnectionInvitationSchema(), required=True)
    message = fields.Str(
        required=False,
        allow_none=True,
        metadata={
            "description": "Comments on the introduction",
            "example": "Hello Bob, it's Alice",
        },
    )
