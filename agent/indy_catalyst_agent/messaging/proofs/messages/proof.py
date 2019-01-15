"""
A proof content message.
"""

from marshmallow import Schema, fields, post_load

from ...agent_message import AgentMessage
from ...message_types import MessageTypes


class Proof(AgentMessage):
    def __init__(self, proof_json: str, request_nonce: str):
        self.proof_json = proof_json
        self.request_nonce = request_nonce

    @property
    # Avoid clobbering builtin property
    def _type(self):
        return MessageTypes.PROOF.value

    @classmethod
    def deserialize(cls, obj):
        return ProofSchema().load(obj)

    def serialize(self):
        return ProofSchema().dump(self)


class ProofSchema(Schema):
    # Avoid clobbering builtin property
    _type = fields.Str(data_key="@type", required=True)
    proof_json = fields.Str(required=True)
    request_nonce = fields.Str(required=True)

    @post_load
    def make_model(self, data: dict) -> Proof:
        del data["_type"]
        return Proof(**data)
