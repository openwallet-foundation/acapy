"""Delete existing forwarding routes."""

from marshmallow import fields
from typing import Sequence

from ...agent_message import AgentMessage, AgentMessageSchema
from ..message_types import DELETE_ROUTES

HANDLER_CLASS = "indy_catalyst_agent.messaging.routing.handlers"
".delete_routes_handler.DeleteRoutesHandler"


class DeleteRoutes(AgentMessage):
    """Delete existing forwarding routes."""

    class Meta:
        """DeleteRoutes metadata."""

        handler_class = HANDLER_CLASS
        message_type = DELETE_ROUTES
        schema_class = "DeleteRoutesSchema"

    def __init__(self, *, recipient_keys: Sequence[str] = None, **kwargs):
        """
        Initialize a DeleteRoutes message instance.

        Args:
            recipient_keys: The keys for the new routes to create
        """

        super(DeleteRoutes, self).__init__(**kwargs)
        self.recipient_keys = list(recipient_keys) if recipient_keys else []


class DeleteRoutesSchema(AgentMessageSchema):
    """DeleteRoutes message schema used in serialization/deserialization."""

    class Meta:
        """DeleteRoutesSchema metadata."""

        model_class = DeleteRoutes

    recipient_keys = fields.List(fields.Str(), required=True)
