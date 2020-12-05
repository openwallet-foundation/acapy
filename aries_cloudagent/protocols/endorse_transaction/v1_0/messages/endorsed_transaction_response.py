"""Represents an endorsed transaction message."""

from marshmallow import EXCLUDE, fields

from .....messaging.agent_message import AgentMessage, AgentMessageSchema

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
        self.endorser_did = endorser_did
        self.state = state


class EndorsedTransactionResponseSchema(AgentMessageSchema):
    """Endorsed transaction response schema class."""

    class Meta:
        """Endorsed transaction response schema metadata."""

        model_class = EndorsedTransactionResponse
        unknown = EXCLUDE

    transaction_id = fields.Str(
        required=False,
        description="The transaction id of the agent who this response is sent to",
    )
    thread_id = fields.Str(
        required=False,
        description="The transaction id of the agent who this response is sent from",
    )
    signature_response = fields.Dict(
        required=False,
    )
    state = fields.Str(
        required=False,
        description="The State of the transaction Record",
        example="ENDORSER",
    )
    endorser_did = fields.Str(
        required=False, description="The public did of the endorser"
    )
