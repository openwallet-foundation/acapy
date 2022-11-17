"""Represents an invitation returned to the introduction service."""

from marshmallow import EXCLUDE, fields

from .....messaging.agent_message import AgentMessage, AgentMessageSchema

from ....connections.v1_0.messages.connection_invitation import (
    ConnectionInvitation,
    ConnectionInvitationSchema,
)

from ..message_types import INVITATION, PROTOCOL_PACKAGE


HANDLER_CLASS = f"{PROTOCOL_PACKAGE}.handlers.invitation_handler.InvitationHandler"


class Invitation(AgentMessage):
    """Class representing an invitation returned to the introduction service."""

    class Meta:
        """Metadata for an invitation."""

        handler_class = HANDLER_CLASS
        message_type = INVITATION
        schema_class = "InvitationSchema"

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


class InvitationSchema(AgentMessageSchema):
    """Invitation request schema class."""

    class Meta:
        """Invitation request schema metadata."""

        model_class = Invitation
        unknown = EXCLUDE

    invitation = fields.Nested(ConnectionInvitationSchema(), required=True)
    message = fields.Str(
        required=False,
        description="Comments on the introduction",
        example="Hello Bob, it's Charlie as Alice mentioned",
        allow_none=True,
    )
