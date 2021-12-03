"""Represents an explicit RFC 15 ack message, adopted into present-proof protocol."""

from marshmallow import EXCLUDE, fields

from .....messaging.agent_message import AgentMessage, AgentMessageSchema

from ..message_types import NOTIF_10_ACK, PROTOCOL_PACKAGE

HANDLER_CLASS = f"{PROTOCOL_PACKAGE}.handlers.ack_handler.V10AckHandler"


class V10Ack(AgentMessage):
    """Base class representing an explicit ack message for no specific protocol."""

    class Meta:
        """V10Ack metadata."""

        handler_class = HANDLER_CLASS
        message_type = NOTIF_10_ACK
        schema_class = "V10AckSchema"

    def __init__(self, status: str = None, **kwargs):
        """
        Initialize an explicit ack message instance.

        Args:
            status: Status (default OK)

        """
        super().__init__(**kwargs)
        self.status = status or "OK"


class V10AckSchema(AgentMessageSchema):
    """Schema for V10Ack class."""

    class Meta:
        """V10Ack schema metadata."""

        model_class = V10Ack
        unknown = EXCLUDE

    status = fields.Str(required=True, description="Status", example="OK")
