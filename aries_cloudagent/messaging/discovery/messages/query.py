"""Represents a protocol discovery query message."""

from marshmallow import fields

from ...agent_message import AgentMessage, AgentMessageSchema
from ..message_types import QUERY

HANDLER_CLASS = (
    "aries_cloudagent.messaging.discovery.handlers.query_handler.QueryHandler"
)


class Query(AgentMessage):
    """Represents a protocol discovery query.

    Used for inspecting what message types are supported by the agent.
    """

    class Meta:
        """Query metadata."""

        handler_class = HANDLER_CLASS
        message_type = QUERY
        schema_class = "QuerySchema"

    def __init__(self, *, query: str = None, comment: str = None, **kwargs):
        """
        Initialize query message object.

        Args:
            query: The query string to match against supported message types
            comment: An optional comment
        """
        super(Query, self).__init__(**kwargs)
        self.query = query
        self.comment = comment


class QuerySchema(AgentMessageSchema):
    """Query message schema used in serialization/deserialization."""

    class Meta:
        """QuerySchema metadata."""

        model_class = Query

    query = fields.Str(required=True)
    comment = fields.Str(required=False)
