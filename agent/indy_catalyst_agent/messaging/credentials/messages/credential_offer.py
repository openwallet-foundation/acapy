"""
A credential offer content message.
"""

from marshmallow import fields

from ...agent_message import AgentMessage, AgentMessageSchema
from ...message_types import MessageTypes


class CredentialOffer(AgentMessage):
    """Class representing a credential offer."""

    class Meta:
        # handler_class = CredentialOfferHandler
        schema_class = "CredentialOfferSchema"
        message_type = MessageTypes.CREDENTIAL_OFFER.value

    def __init__(self, *, offer_json: str = None, **kwargs):
        super(CredentialOffer, self).__init__(**kwargs)
        self.offer_json = offer_json


class CredentialOfferSchema(AgentMessageSchema):
    """Credential offer schema."""

    class Meta:
        model_class = CredentialOffer

    offer_json = fields.Str(required=True)
