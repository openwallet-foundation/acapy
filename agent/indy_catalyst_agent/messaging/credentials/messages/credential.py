"""A credential content message."""

from marshmallow import fields

from ...agent_message import AgentMessage, AgentMessageSchema
from ...message_types import MessageTypes


class Credential(AgentMessage):
    """Class representing a credential."""

    class Meta:
        """Credential metadata."""

        # handler_class = CredentialHandler
        schema_class = "CredentialSchema"
        message_type = MessageTypes.CREDENTIAL.value

    def __init__(
        self,
        *,
        credential_json: str = None,
        revocation_registry_id: str = None,
        **kwargs
    ):
        """
        Initialize credential object.

        Args:
            credential_json (str): Credential offer json string
            revocation_registry_id (str): Credential registry id
        """
        super(Credential, self).__init__(**kwargs)
        self.credential_json = credential_json
        self.revocation_registry_id = revocation_registry_id


class CredentialSchema(AgentMessageSchema):
    """Credential schema."""

    class Meta:
        """Credential schema metadata."""

        model_class = Credential

    credential_json = fields.Str(required=True)
    revocation_registry_id = fields.Str(required=True)
