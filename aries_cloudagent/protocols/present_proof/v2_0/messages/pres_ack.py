"""Represents an explicit RFC 15 ack message, adopted into present-proof protocol."""

from marshmallow import EXCLUDE, fields, validate

from ....notification.v1_0.messages.ack import V10Ack, V10AckSchema

from ..message_types import PRES_20_ACK, PROTOCOL_PACKAGE

HANDLER_CLASS = f"{PROTOCOL_PACKAGE}.handlers.pres_ack_handler.V20PresAckHandler"


class V20PresAck(V10Ack):
    """Base class representing an explicit ack message for present-proof protocol."""

    class Meta:
        """V20PresAck metadata."""

        handler_class = HANDLER_CLASS
        message_type = PRES_20_ACK
        schema_class = "V20PresAckSchema"

    def __init__(self, status: str = None, verification_result: str = None, **kwargs):
        """
        Initialize an explicit ack message instance.

        Args:
            status: Status (default OK)

        """
        super().__init__(status, **kwargs)
        self._verification_result = verification_result


class V20PresAckSchema(V10AckSchema):
    """Schema for V20PresAck class."""

    class Meta:
        """V20PresAck schema metadata."""

        model_class = V20PresAck
        unknown = EXCLUDE

    verification_result = fields.Str(
        required=False,
        description="Whether presentation is verified: true or false",
        example="true",
        validate=validate.OneOf(["true", "false"]),
    )
