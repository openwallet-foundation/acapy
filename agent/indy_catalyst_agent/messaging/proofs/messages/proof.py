"""
A proof content message.
"""

from marshmallow import fields

from ...agent_message import AgentMessage, AgentMessageSchema
from ...message_types import MessageTypes


class Proof(AgentMessage):
    class Meta:
        #handler_class = ProofHandler
        schema_class = 'ProofSchema'
        message_type = MessageTypes.PROOF.value

    def __init__(self, proof_json: str = None, request_nonce: str = None, **kwargs):
        super(Proof, self).__init__(**kwargs)
        self.proof_json = proof_json
        self.request_nonce = request_nonce


class ProofSchema(AgentMessageSchema):
    class Meta:
        model_class = Proof

    # Avoid clobbering builtin property
    proof_json = fields.Str(required=True)
    request_nonce = fields.Str(required=True)
