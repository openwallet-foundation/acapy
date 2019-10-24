"""A credential ack message."""

from ....agent_message import AgentMessage, AgentMessageSchema
from ..message_types import CREDENTIAL_ACK


HANDLER_CLASS = (
    "aries_cloudagent.messaging.issue_credential.v1_0.handlers."
    "credential_ack_handler.CredentialAckHandler"
)


class CredentialAck(AgentMessage):
    """Class representing a credential ack message."""

    class Meta:
        """Credential metadata."""

        handler_class = HANDLER_CLASS
        schema_class = "CredentialAckSchema"
        message_type = CREDENTIAL_ACK

    def __init__(self, **kwargs):
        """Initialize credential object."""
        super().__init__(**kwargs)


class CredentialAckSchema(AgentMessageSchema):
    """Credential ack schema."""

    class Meta:
        """Schema metadata."""

        model_class = CredentialAck
