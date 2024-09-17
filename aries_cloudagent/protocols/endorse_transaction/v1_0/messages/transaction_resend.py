"""Represents a transaction resend message."""

from typing import Optional

from marshmallow import EXCLUDE, fields

from .....messaging.agent_message import AgentMessage, AgentMessageSchema
from .....messaging.valid import UUID4_EXAMPLE
from ..message_types import PROTOCOL_PACKAGE, TRANSACTION_RESEND

HANDLER_CLASS = (
    f"{PROTOCOL_PACKAGE}.handlers.transaction_resend_handler.TransactionResendHandler"
)


class TransactionResend(AgentMessage):
    """Class representing a transaction resend message."""

    class Meta:
        """Metadata for a transaction resend message."""

        handler_class = HANDLER_CLASS
        message_type = TRANSACTION_RESEND
        schema_class = "TransactionResendSchema"

    def __init__(
        self,
        *,
        state: Optional[str] = None,
        thread_id: Optional[str] = None,
        **kwargs,
    ):
        """Initialize a transaction resend object.

        Args:
            state: State of the transaction record
            thread_id: Thread id of transaction record
            kwargs: Additional keyword arguments for the message
        """
        super().__init__(**kwargs)

        self.state = state
        self.thread_id = thread_id


class TransactionResendSchema(AgentMessageSchema):
    """Transaction resend schema class."""

    class Meta:
        """Transaction resend schema metadata."""

        model_class = TransactionResend
        unknown = EXCLUDE

    state = fields.Str(
        required=False,
        metadata={
            "description": "The State of the transaction Record",
            "example": "resend",
        },
    )
    thread_id = fields.Str(required=False, metadata={"example": UUID4_EXAMPLE})
