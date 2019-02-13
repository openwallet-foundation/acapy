"""
A proof request content message.
"""

from marshmallow import fields

from ...agent_message import AgentMessage, AgentMessageSchema
from ...message_types import MessageTypes


class ProofRequest(AgentMessage):
    class Meta:
        # handler_class = ProofRequestHandler
        message_type = MessageTypes.PROOF_REQUEST.value
        schema_class = "ProofRequestSchema"

    def __init__(self, proof_request_json: str = None, **kwargs):
        super(ProofRequest, self).__init__(**kwargs)
        self.proof_request_json = proof_request_json


class ProofRequestSchema(AgentMessageSchema):
    class Meta:
        model_class = ProofRequest

    proof_request_json = fields.Str(required=True)
