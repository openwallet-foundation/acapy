"""
Create new forwarding routes
"""

from marshmallow import fields
from typing import Sequence

from ...agent_message import AgentMessage, AgentMessageSchema
from ..message_types import CREATE_ROUTES

HANDLER_CLASS = "indy_catalyst_agent.messaging.routing.handlers"
".create_routes_handler.CreateRoutesHandler"


class CreateRoutes(AgentMessage):
    """Create new routing rules"""

    class Meta:
        """ """

        handler_class = HANDLER_CLASS
        message_type = CREATE_ROUTES
        schema_class = "CreateRoutesSchema"

    def __init__(self, recipient_keys: Sequence[str] = None, msg: str = None, **kwargs):
        super(CreateRoutes, self).__init__(**kwargs)
        self.recipient_keys = list(recipient_keys) if recipient_keys else []


class CreateRoutesSchema(AgentMessageSchema):
    """ """

    class Meta:
        """ """

        model_class = CreateRoutes

    recipient_keys = fields.List(fields.Str(), required=True)
