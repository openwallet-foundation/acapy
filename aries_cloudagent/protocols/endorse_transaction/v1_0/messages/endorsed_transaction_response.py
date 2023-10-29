"""Represents an endorsed transaction message."""

from marshmallow import EXCLUDE, fields

from .....messaging.agent_message import AgentMessage, AgentMessageSchema
from .....messaging.valid import UUID4_EXAMPLE
from ..message_types import ENDORSED_TRANSACTION_RESPONSE, PROTOCOL_PACKAGE

HANDLER_CLASS = (
    f"{PROTOCOL_PACKAGE}.handlers"
    ".endorsed_transaction_response_handler.EndorsedTransactionResponseHandler"
)


class EndorsedTransactionResponse(AgentMessage):
    """Class representing an endorsed transaction response message."""

    class Meta:
        """Metadata for an endorsed transaction response message."""

        handler_class = HANDLER_CLASS
        message_type = ENDORSED_TRANSACTION_RESPONSE
        schema_class = "EndorsedTransactionResponseSchema"

    def __init__(
        self,
        *,
        transaction_id: str = None,
        thread_id: str = None,
        signature_response: dict = None,
        state: str = None,
        endorser_did: str = None,
        ledger_response: dict = None,
        **kwargs,
    ):
        """
        Initialize an endorsed transaction response object.

        Args:
            transaction_id: The id of the transaction record
            thread_id: The thread id of the transaction record
            signature_response: The response created to endorse the transaction
            state: The state of the transaction record
            endorser_did: The public did of the endorser who endorses the transaction
        """
        super().__init__(**kwargs)

        self.transaction_id = transaction_id
        self.thread_id = thread_id
        self.signature_response = signature_response
        self.state = state
        self.endorser_did = endorser_did
        self.ledger_response = ledger_response


class EndorsedTransactionResponseSchema(AgentMessageSchema):
    """Endorsed transaction response schema class."""

    class Meta:
        """Endorsed transaction response schema metadata."""

        model_class = EndorsedTransactionResponse
        unknown = EXCLUDE

    transaction_id = fields.Str(
        required=False,
        metadata={
            "description": (
                "The transaction id of the agent who this response is sent to"
            ),
            "example": UUID4_EXAMPLE,
        },
    )
    thread_id = fields.Str(
        required=False,
        metadata={
            "description": (
                "The transaction id of the agent who this response is sent from"
            ),
            "example": UUID4_EXAMPLE,
        },
    )
    signature_response = fields.Dict(
        required=False,
        metadata={
            "example": {
                "message_id": "143c458d-1b1c-40c7-ab85-4d16808ddf0a",
                "context": "did:sov",
                "method": "add-signature",
                "signer_goal_code": "transaction.endorse",
                "signature_type": "<requested signature type>",
                "signature": {
                    "4cU41vWW82ArfxJxHkzXPG": (
                        "2yAeV5ftuasWNgQwVYzeHeTuM7LwwNtPR3Zg9N4JiDgF"
                    )
                },
            }
        },
    )
    state = fields.Str(
        required=False,
        metadata={
            "description": "The State of the transaction Record",
            "example": "endorsed",
        },
    )
    endorser_did = fields.Str(
        required=False,
        metadata={
            "description": "The public did of the endorser",
            "example": "V4SGRU86Z58d6TV7PBUe6f",
        },
    )
    ledger_response = fields.Dict(required=False)
