"""Credential ack message."""

from marshmallow import EXCLUDE

from ....notification.v1_0.messages.ack import V10Ack, V10AckSchema

from ..message_types import CRED_20_ACK, PROTOCOL_PACKAGE

HANDLER_CLASS = f"{PROTOCOL_PACKAGE}.handlers.cred_ack_handler.V20CredAckHandler"


class V20CredAck(V10Ack):
    """Credential ack."""

    class Meta:
        """Credential ack metadata."""

        handler_class = HANDLER_CLASS
        schema_class = "V20CredAckSchema"
        message_type = CRED_20_ACK

    def __init__(self, **kwargs):
        """Initialize credential object."""
        super().__init__(**kwargs)


class V20CredAckSchema(V10AckSchema):
    """Credential ack schema."""

    class Meta:
        """Schema metadata."""

        model_class = V20CredAck
        unknown = EXCLUDE
