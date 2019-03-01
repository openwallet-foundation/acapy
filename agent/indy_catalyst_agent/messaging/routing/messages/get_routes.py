"""Request existing forwarding routes."""

from ...agent_message import AgentMessage, AgentMessageSchema
from ..message_types import GET_ROUTES

HANDLER_CLASS = "indy_catalyst_agent.messaging.routing.handlers"
".get_routes_handler.GetRoutesHandler"


class GetRoutes(AgentMessage):
    """Request the list of defined routes for this sender."""

    class Meta:
        """GetRoutes metadata."""

        handler_class = HANDLER_CLASS
        message_type = GET_ROUTES
        schema_class = "GetRoutesSchema"


class GetRoutesSchema(AgentMessageSchema):
    """GetRoutes message schema used in serialization/deserialization."""

    class Meta:
        """GetRoutesSchema metadata."""

        model_class = GetRoutes
