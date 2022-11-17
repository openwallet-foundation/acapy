"""A credential ack message."""

from marshmallow import EXCLUDE

from ....notification.v1_0.messages.ack import V10Ack, V10AckSchema

from ..message_types import CREDENTIAL_ACK, PROTOCOL_PACKAGE

HANDLER_CLASS = (
    f"{PROTOCOL_PACKAGE}.handlers.credential_ack_handler.CredentialAckHandler"
)


class CredentialAck(V10Ack):
    """Class representing a credential ack message."""

    class Meta:
        """Credential ack metadata."""

        handler_class = HANDLER_CLASS
        schema_class = "CredentialAckSchema"
        message_type = CREDENTIAL_ACK

    def __init__(self, **kwargs):
        """Initialize credential ack object."""
        super().__init__(**kwargs)


class CredentialAckSchema(V10AckSchema):
    """Credential ack schema."""

    class Meta:
        """Schema metadata."""

        model_class = CredentialAck
        unknown = EXCLUDE
