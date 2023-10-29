"""Represents a cancel transaction message."""

from marshmallow import EXCLUDE, fields

from .....messaging.agent_message import AgentMessage, AgentMessageSchema
from .....messaging.valid import UUID4_EXAMPLE
from ..message_types import CANCEL_TRANSACTION, PROTOCOL_PACKAGE

HANDLER_CLASS = (
    f"{PROTOCOL_PACKAGE}.handlers.transaction_cancel_handler.TransactionCancelHandler"
)


class CancelTransaction(AgentMessage):
    """Class representing a cancel transaction message."""

    class Meta:
        """Metadata for a cancel transaction message."""

        handler_class = HANDLER_CLASS
        message_type = CANCEL_TRANSACTION
        schema_class = "CancelTransactionSchema"

    def __init__(
        self,
        *,
        state: str = None,
        thread_id: str = None,
        **kwargs,
    ):
        """
        Initialize a cancel transaction object.

        Args:
            state: State of the transaction record
            thread_id: Thread id of transaction record
        """
        super().__init__(**kwargs)

        self.state = state
        self.thread_id = thread_id


class CancelTransactionSchema(AgentMessageSchema):
    """Cancel transaction schema class."""

    class Meta:
        """Cancel transaction schema metadata."""

        model_class = CancelTransaction
        unknown = EXCLUDE

    state = fields.Str(
        required=False,
        metadata={
            "description": "The State of the transaction Record",
            "example": "cancelled",
        },
    )
    thread_id = fields.Str(required=False, metadata={"example": UUID4_EXAMPLE})
