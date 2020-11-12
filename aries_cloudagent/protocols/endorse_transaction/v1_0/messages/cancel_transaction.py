
from marshmallow import EXCLUDE, fields

from .....messaging.agent_message import AgentMessage, AgentMessageSchema

from ..message_types import CANCEL_TRANSACTION, PROTOCOL_PACKAGE

HANDLER_CLASS = (
    f"{PROTOCOL_PACKAGE}.handlers"
    ".transaction_cancel_handler.TransactionCancelHandler"
)


class CancelTransaction(AgentMessage):

    class Meta:

        handler_class = HANDLER_CLASS
        message_type = CANCEL_TRANSACTION
        schema_class = "CancelTransactionSchema"

    def __init__(
        self,
        *,
        state:str = None,
        thread_id:str = None,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.state = state
        self.thread_id = thread_id


class CancelTransactionSchema(AgentMessageSchema):

    class Meta:

        model_class = CancelTransaction
        unknown = EXCLUDE

    state = fields.Str(
        required=False,
        description="The State of the transaction Record",
        example="ENDORSER",
    )
    thread_id = fields.Str(
        required=False
    ) 