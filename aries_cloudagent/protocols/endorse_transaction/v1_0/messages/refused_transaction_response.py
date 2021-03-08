"""Represents a refused transaction message."""

from marshmallow import EXCLUDE, fields

from .....messaging.agent_message import AgentMessage, AgentMessageSchema
from .....messaging.valid import UUIDFour

from ..message_types import REFUSED_TRANSACTION_RESPONSE, PROTOCOL_PACKAGE

HANDLER_CLASS = (
    f"{PROTOCOL_PACKAGE}.handlers"
    ".refused_transaction_response_handler.RefusedTransactionResponseHandler"
)


class RefusedTransactionResponse(AgentMessage):
    """Class representing a refused transaction response message."""

    class Meta:
        """Metadata for a refused transaction response message."""

        handler_class = HANDLER_CLASS
        message_type = REFUSED_TRANSACTION_RESPONSE
        schema_class = "RefusedTransactionResponseSchema"

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
        Initialize a refused transaction response object.

        Args:
            transaction_id: The id of the transaction record
            thread_id: The thread id of the transaction record
            signature_response: The response created to refuse the transaction
            state: The state of the transaction record
            endorser_did: The public did of the endorser who refuses the transaction
        """
        super().__init__(**kwargs)

        self.transaction_id = transaction_id
        self.thread_id = thread_id
        self.signature_response = signature_response
        self.state = state
        self.endorser_did = endorser_did


class RefusedTransactionResponseSchema(AgentMessageSchema):
    """Refused transaction response schema class."""

    class Meta:
        """Refused transaction response schema metadata."""

        model_class = RefusedTransactionResponse
        unknown = EXCLUDE

    transaction_id = fields.Str(
        required=False,
        description="The transaction id of the agent who this response is sent to",
        example=UUIDFour.EXAMPLE,
    )
    thread_id = fields.Str(
        required=False,
        description="The transaction id of the agent who this response is sent from",
        example=UUIDFour.EXAMPLE,
    )
    signature_response = fields.Dict(
        required=False,
        example={
            "message_id": "143c458d-1b1c-40c7-ab85-4d16808ddf0a",
            "context": "did:sov",
            "method": "add-signature",
            "signer_goal_code": "transaction.refuse",
        },
    )
    state = fields.Str(
        required=False,
        description="The State of the transaction Record",
        example="refused",
    )
    endorser_did = fields.Str(
        required=False,
        description="The public did of the endorser",
        example="V4SGRU86Z58d6TV7PBUe6f",
    )
