"""Revoke message."""

from marshmallow import fields

from .....messaging.agent_message import AgentMessage, AgentMessageSchema
from .....messaging.valid import UUID4_EXAMPLE
from ..message_types import PROTOCOL_PACKAGE, REVOKE

HANDLER_CLASS = f"{PROTOCOL_PACKAGE}.handlers.revoke_handler.RevokeHandler"


class Revoke(AgentMessage):
    """Class representing revoke message."""

    class Meta:
        """Revoke Meta."""

        handler_class = HANDLER_CLASS
        message_type = REVOKE
        schema_class = "RevokeSchema"

    def __init__(self, *, thread_id: str, comment: str = None, **kwargs):
        """Initialize revoke message."""
        super().__init__(**kwargs)
        # TODO support please ack
        self.thread_id = thread_id
        self.comment = comment


class RevokeSchema(AgentMessageSchema):
    """Schema of Revoke message."""

    class Meta:
        """RevokeSchema Meta."""

        model_class = Revoke

    # TODO support please ack
    thread_id = fields.Str(
        required=True,
        metadata={
            "description": (
                "Thread ID of credential exchange resulting in this issued credential"
            ),
            "example": UUID4_EXAMPLE,
        },
    )
    comment = fields.Str(
        required=False,
        metadata={
            "description": "Human readable information about revocation notification"
        },
    )
