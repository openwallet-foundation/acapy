"""
Represents an invitation message for establishing connection.
"""

from datetime import datetime
from typing import Union

from marshmallow import fields

from ...agent_message import AgentMessage, AgentMessageSchema
from ..message_types import BASIC_MESSAGE

HANDLER_CLASS = "indy_catalyst_agent.messaging.basicmessage.handlers.basicmessage_handler.BasicMessageHandler"


class BasicMessage(AgentMessage):
    class Meta:
        handler_class = HANDLER_CLASS
        message_type = BASIC_MESSAGE
        schema_class = "BasicMessageSchema"

    def __init__(
            self,
            *,
            timestamp: Union[str, datetime] = None,
            content: str = None,
            **kwargs,
        ):
        super(BasicMessage, self).__init__(**kwargs)
        if not timestamp:
            timestamp = datetime.utcnow()
        if isinstance(timestamp, datetime):
            timestamp = timestamp.isoformat()
        self.timestamp = timestamp
        self.content = content


class BasicMessageSchema(AgentMessageSchema):
    class Meta:
        model_class = BasicMessage

    timestamp = fields.Str(required=False) # should be called sent_time
    content = fields.Str(required=True)
