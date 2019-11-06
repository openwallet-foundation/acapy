"""A credential request content message."""

from marshmallow import fields

from ....messaging.agent_message import AgentMessage, AgentMessageSchema

from ..message_types import CREDENTIAL_REQUEST, PROTOCOL_PACKAGE

HANDLER_CLASS = (
    f"{PROTOCOL_PACKAGE}.handlers."
    "credential_request_handler.CredentialRequestHandler"
)


class CredentialRequest(AgentMessage):
    """Class representing a credential request."""

    class Meta:
        """CredentialRequest metadata."""

        handler_class = HANDLER_CLASS
        schema_class = "CredentialRequestSchema"
        message_type = CREDENTIAL_REQUEST

    def __init__(self, *, request: str = None, comment: str = None, **kwargs):
        """
        Initialize credential request object.

        Args:
            offer_json: Credential offer json string
            credential_request_json: Credential request json string

        """
        super(CredentialRequest, self).__init__(**kwargs)
        self.request = request
        self.comment = comment


class CredentialRequestSchema(AgentMessageSchema):
    """Credential request schema."""

    class Meta:
        """Credential request schema metadata."""

        model_class = CredentialRequest

    request = fields.Str(required=True)
    comment = fields.Str(required=False)
