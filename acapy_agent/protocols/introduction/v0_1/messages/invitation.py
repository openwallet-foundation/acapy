"""Represents an invitation returned to the introduction service."""

from typing import Optional

from marshmallow import EXCLUDE, fields

from .....messaging.agent_message import AgentMessage, AgentMessageSchema
from ....out_of_band.v1_0.messages.invitation import (
    InvitationMessage,
    InvitationMessageSchema,
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
        self,
        *,
        invitation: Optional[InvitationMessage] = None,
        message: Optional[str] = None,
        **kwargs,
    ):
        """Initialize invitation object.

        Args:
            invitation: The connection invitation
            message: Comments on the introduction
            kwargs: Additional key word arguments for the message
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

    invitation = fields.Nested(InvitationMessageSchema(), required=True)
    message = fields.Str(
        required=False,
        allow_none=True,
        metadata={
            "description": "Comments on the introduction",
            "example": "Hello Bob, it's Charlie as Alice mentioned",
        },
    )
