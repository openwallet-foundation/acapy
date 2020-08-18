"""Represents a feature discovery query message."""

from marshmallow import EXCLUDE, fields

from .....messaging.agent_message import AgentMessage, AgentMessageSchema

from ..message_types import PROTOCOL_PACKAGE, QUERY

HANDLER_CLASS = f"{PROTOCOL_PACKAGE}.handlers.query_handler.QueryHandler"


class Query(AgentMessage):
    """Represents a feature discovery query.

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
        super().__init__(**kwargs)
        self.query = query
        self.comment = comment


class QuerySchema(AgentMessageSchema):
    """Query message schema used in serialization/deserialization."""

    class Meta:
        """QuerySchema metadata."""

        model_class = Query
        unknown = EXCLUDE

    query = fields.Str(required=True)
    comment = fields.Str(required=False, allow_none=True)
