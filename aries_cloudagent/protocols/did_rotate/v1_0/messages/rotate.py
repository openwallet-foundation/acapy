"""Rotate message."""

from marshmallow import EXCLUDE, fields

from .....messaging.agent_message import AgentMessage, AgentMessageSchema
from ..message_types import ROTATE, PROTOCOL_PACKAGE

HANDLER_CLASS = f"{PROTOCOL_PACKAGE}.handlers.rotate_handler.RotateHandler"


class Rotate(AgentMessage):
    """Class representing a rotate message."""

    class Meta:
        """Rotate metadata."""

        handler_class = HANDLER_CLASS
        message_type = ROTATE
        schema_class = "RotateSchema"

    def __init__(self, *, to_did: str, **kwargs):
        """Initialize a Rotate message instance."""
        super().__init__(**kwargs)
        self.to_did = to_did


class RotateSchema(AgentMessageSchema):
    """Schema for Rotate class."""

    class Meta:
        """RotateSchema metadata."""

        model_class = Rotate
        unknown = EXCLUDE

    to_did = fields.Str(
        required=True,
        allow_none=False,
        metadata={
            "description": "The DID the rotating party is rotating to",
            "example": "did:example:newdid",
        },
    )
