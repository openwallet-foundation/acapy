"""
A credential offer content message.
"""

from marshmallow import Schema, fields, post_load

from ...agent_message import AgentMessage
from ...message_types import MessageTypes


class CredentialOffer(AgentMessage):
    def __init__(self, offer_json: str):
        self.offer_json = offer_json

    @property
    # Avoid clobbering builtin property
    def _type(self):
        return MessageTypes.CREDENTIAL_OFFER.value

    @classmethod
    def deserialize(cls, obj):
        return CredentialOfferSchema().load(obj)

    def serialize(self):
        return CredentialOfferSchema().dump(self)


class CredentialOfferSchema(Schema):
    # Avoid clobbering builtin property
    _type = fields.Str(data_key="@type", required=True)
    offer_json = fields.Str(required=True)

    @post_load
    def make_model(self, data: dict) -> CredentialOffer:
        del data["_type"]
        return CredentialOffer(**data)
