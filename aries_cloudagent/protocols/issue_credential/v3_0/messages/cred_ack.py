"""Credential ack message."""

from marshmallow import EXCLUDE

from ....notification.v1_0.messages.ack import V10Ack, V10AckSchema

from ..message_types import CRED_30_ACK, PROTOCOL_PACKAGE

HANDLER_CLASS = f"{PROTOCOL_PACKAGE}.handlers.cred_ack_handler.V30CredAckHandler"


class V30CredAck(V10Ack):
    """Credential ack."""

    class Meta:
        """Credential ack metadata."""

        handler_class = HANDLER_CLASS
        schema_class = "V30CredAckSchema"
        message_type = CRED_30_ACK

    def __init__(self, **kwargs):
        """Initialize credential object."""
        super().__init__(**kwargs)


class V30CredAckSchema(V10AckSchema):
    """Credential ack schema."""

    class Meta:
        """Schema metadata."""

        model_class = V30CredAck
        unknown = EXCLUDE
