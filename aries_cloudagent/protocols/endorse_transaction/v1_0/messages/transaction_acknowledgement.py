"""Represents a transaction acknowledgement message."""

from marshmallow import EXCLUDE, fields

from .....messaging.valid import UUIDFour

from ....notification.v1_0.messages.ack import V10Ack, V10AckSchema

from ..message_types import TRANSACTION_ACKNOWLEDGEMENT, PROTOCOL_PACKAGE

HANDLER_CLASS = (
    f"{PROTOCOL_PACKAGE}.handlers"
    ".transaction_acknowledgement_handler.TransactionAcknowledgementHandler"
)


class TransactionAcknowledgement(V10Ack):
    """Class representing a transaction acknowledgement message."""

    class Meta:
        """Metadata for a transaction acknowledgement message."""

        handler_class = HANDLER_CLASS
        message_type = TRANSACTION_ACKNOWLEDGEMENT
        schema_class = "TransactionAcknowledgementSchema"

    def __init__(
        self,
        *,
        thread_id: str = None,
        ledger_response: dict = None,
        **kwargs,
    ):
        """
        Initialize a transaction acknowledgement object.

        Args:
            thread_id: Thread id of transaction record
        """
        super().__init__(**kwargs)
        self.thread_id = thread_id
        self.ledger_response = ledger_response


class TransactionAcknowledgementSchema(V10AckSchema):
    """Transaction Acknowledgement schema class."""

    class Meta:
        """Transaction Acknowledgement metadata."""

        model_class = TransactionAcknowledgement
        unknown = EXCLUDE

    thread_id = fields.Str(required=True, example=UUIDFour.EXAMPLE)
    ledger_response = fields.Dict(required=False)
