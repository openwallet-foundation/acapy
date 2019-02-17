"""
Delete existing forwarding routes
"""

from marshmallow import fields
from typing import Sequence

from ...agent_message import AgentMessage, AgentMessageSchema
from ..message_types import DELETE_ROUTES

HANDLER_CLASS = "indy_catalyst_agent.messaging.routing.handlers"
".delete_routes_handler.DeleteRoutesHandler"


class DeleteRoutes(AgentMessage):
    """Delete existing forwarding routes"""

    class Meta:
        """ """

        handler_class = HANDLER_CLASS
        message_type = DELETE_ROUTES
        schema_class = "DeleteRoutesSchema"

    def __init__(
        self, *, recipient_keys: Sequence[str] = None, msg: str = None, **kwargs
    ):
        super(DeleteRoutes, self).__init__(**kwargs)
        self.recipient_keys = list(recipient_keys) if recipient_keys else []


class DeleteRoutesSchema(AgentMessageSchema):
    """ """

    class Meta:
        """ """

        model_class = DeleteRoutes

    recipient_keys = fields.List(fields.Str(), required=True)
