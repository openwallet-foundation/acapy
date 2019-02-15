"""
Represents an invitation message for establishing connection.
"""

from datetime import datetime, timezone
from typing import Union

from marshmallow import fields

from ...agent_message import AgentMessage, AgentMessageSchema
from ..message_types import BASIC_MESSAGE

HANDLER_CLASS = (
    "indy_catalyst_agent.messaging.basicmessage."
    + "handlers.basicmessage_handler.BasicMessageHandler"
)


class BasicMessage(AgentMessage):
    class Meta:
        handler_class = HANDLER_CLASS
        message_type = BASIC_MESSAGE
        schema_class = "BasicMessageSchema"

    def __init__(
        self, *, sent_time: Union[str, datetime] = None, content: str = None, **kwargs
    ):
        super(BasicMessage, self).__init__(**kwargs)
        if not sent_time:
            sent_time = datetime.utcnow()
        if isinstance(sent_time, datetime):
            sent_time = sent_time.replace(tzinfo=timezone.utc).isoformat(" ")
        self.sent_time = sent_time
        self.content = content


class BasicMessageSchema(AgentMessageSchema):
    class Meta:
        model_class = BasicMessage

    sent_time = fields.Str(required=False)
    content = fields.Str(required=True)
