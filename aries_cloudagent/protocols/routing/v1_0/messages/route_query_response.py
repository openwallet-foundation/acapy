"""Return existing forwarding routes in response to a query."""

from typing import Sequence

from marshmallow import EXCLUDE, fields

from .....messaging.agent_message import AgentMessage, AgentMessageSchema

from ..message_types import PROTOCOL_PACKAGE, ROUTE_QUERY_RESPONSE
from ..models.paginated import Paginated, PaginatedSchema
from ..models.route_query_result import RouteQueryResult, RouteQueryResultSchema

HANDLER_CLASS = (
    f"{PROTOCOL_PACKAGE}.handlers"
    ".route_query_response_handler.RouteQueryResponseHandler"
)


class RouteQueryResponse(AgentMessage):
    """Return existing routes from a routing agent."""

    class Meta:
        """RouteQueryResponse metadata."""

        handler_class = HANDLER_CLASS
        message_type = ROUTE_QUERY_RESPONSE
        schema_class = "RouteQueryResponseSchema"

    def __init__(
        self,
        *,
        routes: Sequence[RouteQueryResult] = None,
        paginated: Paginated = None,
        **kwargs,
    ):
        """
        Initialize a RouteQueryResponse message instance.

        Args:
            filter: Filter results according to specific field values
        """

        super().__init__(**kwargs)
        self.routes = routes or []
        self.paginated = paginated


class RouteQueryResponseSchema(AgentMessageSchema):
    """RouteQueryResponse message schema used in serialization/deserialization."""

    class Meta:
        """RouteQueryResponseSchema metadata."""

        model_class = RouteQueryResponse
        unknown = EXCLUDE

    routes = fields.List(fields.Nested(RouteQueryResultSchema()), required=True)
    paginated = fields.Nested(PaginatedSchema(), required=False)
