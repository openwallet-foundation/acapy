"""
A credential request content message.
"""

from marshmallow import fields

from ...agent_message import AgentMessage, AgentMessageSchema
from ...message_types import MessageTypes


class CredentialRequest(AgentMessage):
    """Class representing a credential request."""

    class Meta:
        # handler_class = CredentialRequestHandler
        schema_class = "CredentialRequestSchema"
        message_type = MessageTypes.CREDENTIAL_REQUEST.value

    def __init__(
        self,
        *,
        offer_json: str = None,
        credential_request_json: str = None,
        credential_values_json: str = None,
        **kwargs
    ):
        super(CredentialRequest, self).__init__(**kwargs)
        self.offer_json = offer_json
        self.credential_request_json = credential_request_json
        self.credential_values_json = credential_values_json


class CredentialRequestSchema(AgentMessageSchema):
    """Credential request schema."""

    class Meta:
        model_class = CredentialRequest

    offer_json = fields.Str(required=True)
    credential_request_json = fields.Str(required=True)
    credential_values_json = fields.Str(required=True)
