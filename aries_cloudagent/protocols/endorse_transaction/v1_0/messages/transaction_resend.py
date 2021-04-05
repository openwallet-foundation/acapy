"""Represents a transaction resend message."""

from marshmallow import EXCLUDE, fields

from .....messaging.agent_message import AgentMessage, AgentMessageSchema
from .....messaging.valid import UUIDFour

from ..message_types import TRANSACTION_RESEND, PROTOCOL_PACKAGE

HANDLER_CLASS = (
    f"{PROTOCOL_PACKAGE}.handlers"
    ".transaction_resend_handler.TransactionResendHandler"
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
        state: str = None,
        thread_id: str = None,
        **kwargs,
    ):
        """
        Initialize a transaction resend object.

        Args:
            state: State of the transaction record
            thread_id: Thread id of transaction record
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
        description="The State of the transaction Record",
        example="resend",
    )
    thread_id = fields.Str(required=False, example=UUIDFour.EXAMPLE)
