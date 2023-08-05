"""Represents a Transaction Job to send message."""

from marshmallow import EXCLUDE, fields

from .....messaging.agent_message import AgentMessage, AgentMessageSchema
from ..message_types import PROTOCOL_PACKAGE, TRANSACTION_JOB_TO_SEND

HANDLER_CLASS = (
    f"{PROTOCOL_PACKAGE}.handlers"
    ".transaction_job_to_send_handler.TransactionJobToSendHandler"
)


class TransactionJobToSend(AgentMessage):
    """Class representing a transaction job to send."""

    class Meta:
        """Metadata for a TransactionJobToSend."""

        handler_class = HANDLER_CLASS
        message_type = TRANSACTION_JOB_TO_SEND
        schema_class = "TransactionJobToSendSchema"

    def __init__(
        self,
        *,
        job: str = None,
        **kwargs,
    ):
        """
        Initialize transaction job to send.

        Args:
            job: The job that needs to be send

        """

        super().__init__(**kwargs)
        self.job = job


class TransactionJobToSendSchema(AgentMessageSchema):
    """Transaction Job to send schema class."""

    class Meta:
        """Metadata for a TransactionJobToSendSchema."""

        model_class = TransactionJobToSend
        unknown = EXCLUDE

    job = fields.Str(
        required=True,
        metadata={
            "description": "Transaction job that is sent to the other agent",
            "example": "TRANSACTION_AUTHOR",
        },
    )
