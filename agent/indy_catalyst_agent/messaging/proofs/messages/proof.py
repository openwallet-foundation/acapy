"""A proof content message."""

from marshmallow import fields

from ...agent_message import AgentMessage, AgentMessageSchema
from ...message_types import MessageTypes


class Proof(AgentMessage):
    """Class representing a proof."""

    class Meta:
        """Proof metadata."""

        # handler_class = ProofHandler
        schema_class = "ProofSchema"
        message_type = MessageTypes.PROOF.value

    def __init__(self, proof_json: str = None, request_nonce: str = None, **kwargs):
        """
        Initialize proof object.

        Args:
            proof_json (str): Proof json string
            request_nonce (str): Proof request nonce
        """
        super(Proof, self).__init__(**kwargs)
        self.proof_json = proof_json
        self.request_nonce = request_nonce


class ProofSchema(AgentMessageSchema):
    """Proof schema."""

    class Meta:
        """ProofSchema metadata."""

        model_class = Proof

    # Avoid clobbering builtin property
    proof_json = fields.Str(required=True)
    request_nonce = fields.Str(required=True)
