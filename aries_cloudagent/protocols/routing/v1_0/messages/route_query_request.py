"""Query existing forwarding routes."""

from marshmallow import EXCLUDE, fields

from .....messaging.agent_message import AgentMessage, AgentMessageSchema
from ..message_types import PROTOCOL_PACKAGE, ROUTE_QUERY_REQUEST
from ..models.paginate import Paginate, PaginateSchema

HANDLER_CLASS = (
    f"{PROTOCOL_PACKAGE}.handlers.route_query_request_handler.RouteQueryRequestHandler"
)


class RouteQueryRequest(AgentMessage):
    """Query existing routes from a routing agent."""

    class Meta:
        """RouteQueryRequest metadata."""

        handler_class = HANDLER_CLASS
        message_type = ROUTE_QUERY_REQUEST
        schema_class = "RouteQueryRequestSchema"

    def __init__(self, *, filter: dict = None, paginate: Paginate = None, **kwargs):
        """
        Initialize a RouteQueryRequest message instance.

        Args:
            filter: Filter results according to specific field values
        """

        super().__init__(**kwargs)
        self.filter = filter
        self.paginate = paginate


class RouteQueryRequestSchema(AgentMessageSchema):
    """RouteQueryRequest message schema used in serialization/deserialization."""

    class Meta:
        """RouteQueryRequestSchema metadata."""

        model_class = RouteQueryRequest
        unknown = EXCLUDE

    filter = fields.Dict(
        keys=fields.Str(metadata={"description": "field"}),
        values=fields.List(
            fields.Str(metadata={"description": "value"}),
            metadata={"description": "List of values"},
        ),
        required=False,
        allow_none=True,
        metadata={"description": "Filter by field name and value"},
    )
    paginate = fields.Nested(PaginateSchema(), required=False, allow_none=True)
