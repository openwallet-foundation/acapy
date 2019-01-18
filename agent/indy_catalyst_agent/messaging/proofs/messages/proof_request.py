"""
A proof request content message.
"""

from marshmallow import Schema, fields, post_load

from ...agent_message import AgentMessage
from ...message_types import MessageTypes


class ProofRequest(AgentMessage):
    def __init__(self, proof_request_json: str):
        self.proof_request_json = proof_request_json

    @property
    # Avoid clobbering builtin property
    def _type(self):
        return MessageTypes.PROOF_REQUEST.value

    @classmethod
    def deserialize(cls, obj):
        return ProofRequestSchema().load(obj)

    def serialize(self):
        return ProofRequestSchema().dump(self)


class ProofRequestSchema(Schema):
    # Avoid clobbering builtin property
    _type = fields.Str(data_key="@type", required=True)
    proof_request_json = fields.Str(required=True)

    @post_load
    def make_model(self, data: dict) -> ProofRequest:
        del data["_type"]
        return ProofRequest(**data)
