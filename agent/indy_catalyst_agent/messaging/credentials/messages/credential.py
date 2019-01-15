"""
A credential content message.
"""

from marshmallow import Schema, fields, post_load

from ...agent_message import AgentMessage
from ...message_types import MessageTypes


class Credential(AgentMessage):
    def __init__(self, credential_json: str, revocation_registry_id: str):
        self.credential_json = credential_json
        self.revocation_registry_id = revocation_registry_id

    @property
    # Avoid clobbering builtin property
    def _type(self):
        return MessageTypes.CREDENTIAL.value

    @classmethod
    def deserialize(cls, obj):
        return CredentialSchema().load(obj)

    def serialize(self):
        return CredentialSchema().dump(self)


class CredentialSchema(Schema):
    # Avoid clobbering builtin property
    _type = fields.Str(data_key="@type", required=True)
    credential_json = fields.Str(required=True)
    revocation_registry_id = fields.Str(required=True)

    @post_load
    def make_model(self, data: dict) -> Credential:
        del data["_type"]
        return Credential(**data)
