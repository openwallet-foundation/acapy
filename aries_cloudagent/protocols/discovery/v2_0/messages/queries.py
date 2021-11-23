"""Represents a feature discovery queries message."""

from typing import Sequence
from marshmallow import EXCLUDE, fields, validate

from .....messaging.agent_message import AgentMessage, AgentMessageSchema
from .....messaging.models.base import BaseModel, BaseModelSchema

from ..message_types import PROTOCOL_PACKAGE, QUERIES

HANDLER_CLASS = f"{PROTOCOL_PACKAGE}.handlers.queries_handler.QueriesHandler"


class QueryItem(BaseModel):
    """Defines QueryItem field."""

    class Meta:
        """QueryItem metadata."""

        schema_class = "QueryItemSchema"

    def __init__(
        self,
        *,
        feature_type: str,
        match: str,
    ):
        """Initialize QueryItem."""
        self.feature_type = feature_type
        self.match = match


class QueryItemSchema(BaseModelSchema):
    """Single QueryItem Schema."""

    class Meta:
        """QueryItemSchema metadata."""

        model_class = QueryItem
        unknown = EXCLUDE

    feature_type = fields.Str(
        required=True,
        description="feature type",
        data_key="feature-type",
        validate=validate.OneOf(["protocol", "goal-code"]),
    )
    match = fields.Str(required=True, description="match")


class Queries(AgentMessage):
    """Represents a discover-features v2 queries message.

    Used for inspecting what message types are supported by the agent.
    """

    class Meta:
        """Queries metadata."""

        handler_class = HANDLER_CLASS
        message_type = QUERIES
        schema_class = "QueriesSchema"

    def __init__(self, *, queries: Sequence[QueryItem] = None, **kwargs):
        """
        Initialize query message object.

        Args:
            query: The query string to match against supported message types
            comment: An optional comment
        """
        super().__init__(**kwargs)
        self.queries = queries


class QueriesSchema(AgentMessageSchema):
    """Query message schema used in serialization/deserialization."""

    class Meta:
        """QuerySchema metadata."""

        model_class = Queries
        unknown = EXCLUDE

    queries = fields.List(fields.Nested(QueryItemSchema))
