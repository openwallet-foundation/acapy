"""Represents an explicit RFC 15 ack message, adopted into present-proof protocol."""

from .....messaging.ack.message import Ack, AckSchema
from ..message_types import PRESENTATION_ACK, PROTOCOL_PACKAGE


HANDLER_CLASS = (
    f"{PROTOCOL_PACKAGE}.handlers.presentation_ack_handler.PresentationAckHandler"
)


class PresentationAck(Ack):
    """Base class representing an explicit ack message for present-proof protocol."""

    class Meta:
        """PresentationAck metadata."""

        handler_class = HANDLER_CLASS
        message_type = PRESENTATION_ACK
        schema_class = "PresentationAckSchema"

    def __init__(self, status: str = None, **kwargs):
        """
        Initialize an explicit ack message instance.

        Args:
            status: Status (default OK)

        """
        super().__init__(status, **kwargs)


class PresentationAckSchema(AckSchema):
    """Schema for PresentationAck class."""

    class Meta:
        """PresentationAck schema metadata."""

        model_class = PresentationAck
