"""Request to update forwarding routes."""

from typing import Sequence

from marshmallow import EXCLUDE, fields

from .....messaging.agent_message import AgentMessage, AgentMessageSchema

from ..message_types import PROTOCOL_PACKAGE, ROUTE_UPDATE_REQUEST
from ..models.route_update import RouteUpdate, RouteUpdateSchema

HANDLER_CLASS = (
    f"{PROTOCOL_PACKAGE}.handlers"
    ".route_update_request_handler.RouteUpdateRequestHandler"
)


class RouteUpdateRequest(AgentMessage):
    """Request to existing routes with a routing agent."""

    class Meta:
        """RouteUpdateRequest metadata."""

        handler_class = HANDLER_CLASS
        message_type = ROUTE_UPDATE_REQUEST
        schema_class = "RouteUpdateRequestSchema"

    def __init__(self, *, updates: Sequence[RouteUpdate] = None, **kwargs):
        """
        Initialize a RouteUpdateRequest message instance.

        Args:
            updates: A list of route updates
        """

        super().__init__(**kwargs)
        self.updates = updates or []


class RouteUpdateRequestSchema(AgentMessageSchema):
    """RouteUpdateRequest message schema used in serialization/deserialization."""

    class Meta:
        """RouteUpdateRequestSchema metadata."""

        model_class = RouteUpdateRequest
        unknown = EXCLUDE

    updates = fields.List(fields.Nested(RouteUpdateSchema()), required=True)
