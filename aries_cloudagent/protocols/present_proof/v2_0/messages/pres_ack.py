"""Represents an explicit RFC 15 ack message, adopted into present-proof protocol."""

from marshmallow import EXCLUDE

from .....messaging.ack.message import Ack, AckSchema

from ..message_types import PRES_ACK, PROTOCOL_PACKAGE

HANDLER_CLASS = (
    f"{PROTOCOL_PACKAGE}.handlers.pres_ack_handler.PresAckHandler"
)


class PresAck(Ack):
    """Base class representing an explicit ack message for present-proof protocol."""

    class Meta:
        """PresAck metadata."""

        handler_class = HANDLER_CLASS
        message_type = PRES_ACK
        schema_class = "PresAckSchema"

    def __init__(self, status: str = None, **kwargs):
        """
        Initialize an explicit ack message instance.

        Args:
            status: Status (default OK)

        """
        super().__init__(status, **kwargs)


class PresAckSchema(AckSchema):
    """Schema for PresAck class."""

    class Meta:
        """PresAck schema metadata."""

        model_class = PresAck
        unknown = EXCLUDE
