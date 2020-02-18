"""A credential stored message."""

from ....messaging.agent_message import AgentMessage, AgentMessageSchema

from ..message_types import CREDENTIAL_STORED, PROTOCOL_PACKAGE

HANDLER_CLASS = (
    f"{PROTOCOL_PACKAGE}.handlers.credential_stored_handler.CredentialStoredHandler"
)


class CredentialStored(AgentMessage):
    """Class representing a credential stored message."""

    class Meta:
        """Credential metadata."""

        handler_class = HANDLER_CLASS
        schema_class = "CredentialStoredSchema"
        message_type = CREDENTIAL_STORED

    def __init__(self, **kwargs):
        """Initialize credential object."""
        super(CredentialStored, self).__init__(**kwargs)


class CredentialStoredSchema(AgentMessageSchema):
    """Credential stored schema."""

    class Meta:
        """Schema metadata."""

        model_class = CredentialStored
