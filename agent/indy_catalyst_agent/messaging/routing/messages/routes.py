"""
Return the current set of forwarding routes
"""

from marshmallow import fields
from typing import Sequence

from ...agent_message import AgentMessage, AgentMessageSchema
from ..message_types import ROUTES

HANDLER_CLASS = "indy_catalyst_agent.messaging.routing.handlers"
".routes_handler.RoutesHandler"


class Routes(AgentMessage):
    """Return the current set of forwarding routes"""

    class Meta:
        """ """

        handler_class = HANDLER_CLASS
        message_type = ROUTES
        schema_class = "RoutesSchema"

    def __init__(self, *, recipient_keys: Sequence[str] = None, **kwargs):
        super(Routes, self).__init__(**kwargs)
        self.recipient_keys = list(recipient_keys) if recipient_keys else []


class RoutesSchema(AgentMessageSchema):
    """ """

    class Meta:
        """ """

        model_class = Routes

    recipient_keys = fields.List(fields.Str(), required=True)
