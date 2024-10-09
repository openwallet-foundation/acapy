"""Rotate ack message."""

from marshmallow import EXCLUDE, ValidationError, pre_dump

from ....notification.v1_0.messages.ack import V10Ack, V10AckSchema
from ..message_types import ACK, PROTOCOL_PACKAGE

HANDLER_CLASS = f"{PROTOCOL_PACKAGE}.handlers.ack_handler.RotateAckHandler"


class RotateAck(V10Ack):
    """Rotate ack."""

    class Meta:
        """Rotate ack metadata."""

        handler_class = HANDLER_CLASS
        schema_class = "RotateAckSchema"
        message_type = ACK

    def __init__(self, **kwargs):
        """Initialize rotate ack object."""
        super().__init__(**kwargs)


class RotateAckSchema(V10AckSchema):
    """Rotate ack schema."""

    class Meta:
        """Schema metadata."""

        model_class = RotateAck
        unknown = EXCLUDE

    @pre_dump
    def check_thread_deco(self, obj, **kwargs):
        """Thread decorator, and its thid, are mandatory."""
        if not obj._decorators.to_dict().get("~thread", {}).keys() >= {"thid"}:
            raise ValidationError("Missing required field(s) in thread decorator")
        return obj
