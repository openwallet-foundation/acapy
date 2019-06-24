"""Query existing forwarding routes."""

from marshmallow import fields

from ...agent_message import AgentMessage, AgentMessageSchema
from ..message_types import ROUTE_QUERY_REQUEST
from ..models.paginate import Paginate, PaginateSchema

HANDLER_CLASS = (
    "aries_cloudagent.messaging.routing.handlers"
    + ".route_query_request_handler.RouteQueryRequestHandler"
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

        super(RouteQueryRequest, self).__init__(**kwargs)
        self.filter = filter
        self.paginate = paginate


class RouteQueryRequestSchema(AgentMessageSchema):
    """RouteQueryRequest message schema used in serialization/deserialization."""

    class Meta:
        """RouteQueryRequestSchema metadata."""

        model_class = RouteQueryRequest

    filter = fields.Dict(
        fields.Str(), fields.List(fields.Str()), required=False, allow_none=True
    )
    paginate = fields.Nested(PaginateSchema(), required=False, allow_none=True)
