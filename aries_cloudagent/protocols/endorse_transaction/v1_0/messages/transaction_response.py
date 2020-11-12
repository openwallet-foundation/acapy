from marshmallow import EXCLUDE, fields

from .....messaging.agent_message import AgentMessage, AgentMessageSchema

from ..message_types import TRANSACTION_RESPONSE, PROTOCOL_PACKAGE

HANDLER_CLASS = (
    f"{PROTOCOL_PACKAGE}.handlers"
    ".transaction_response_handler.TransactionResponseHandler"
)


class TransactionResponse(AgentMessage):

    class Meta:

        handler_class = HANDLER_CLASS
        message_type = TRANSACTION_RESPONSE
        schema_class = "TransactionResponseSchema"

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


class TransactionResponseSchema(AgentMessageSchema):

    class Meta:

        model_class = TransactionResponse
        unknown = EXCLUDE


    state = fields.Str(
        required=False,
        description="The State of the transaction Record",
        example="ENDORSER",
    )

    thread_id = fields.Str(
        required=False,
    )  

