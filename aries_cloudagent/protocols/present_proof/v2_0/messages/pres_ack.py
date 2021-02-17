"""Represents an explicit RFC 15 ack message, adopted into present-proof protocol."""

from marshmallow import EXCLUDE

from .....messaging.ack.message import Ack, AckSchema

from ..message_types import PRES_20_ACK, PROTOCOL_PACKAGE

HANDLER_CLASS = f"{PROTOCOL_PACKAGE}.handlers.pres_ack_handler.V20PresAckHandler"


class V20PresAck(Ack):
    """Base class representing an explicit ack message for present-proof protocol."""

    class Meta:
        """V20PresAck metadata."""

        handler_class = HANDLER_CLASS
        message_type = PRES_20_ACK
        schema_class = "V20PresAckSchema"

    def __init__(self, status: str = None, **kwargs):
        """
        Initialize an explicit ack message instance.

        Args:
            status: Status (default OK)

        """
        super().__init__(status, **kwargs)


class V20PresAckSchema(AckSchema):
    """Schema for V20PresAck class."""

    class Meta:
        """V20PresAck schema metadata."""

        model_class = V20PresAck
        unknown = EXCLUDE
