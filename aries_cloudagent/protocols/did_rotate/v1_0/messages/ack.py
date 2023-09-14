"""Rotate ack message."""

from marshmallow import EXCLUDE, ValidationError, validates_schema

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

    @validates_schema
    def validate_fields(self, data, **kwargs):
        """Validate schema fields.

        Args:
            data: The data to validate

        Raises:
            ValidationError: if data is invalid

        """
        if "~thread" not in data or "thid" not in data["~thread"]:
            raise ValidationError("Rotate problem report must contain ~thread.thid")
