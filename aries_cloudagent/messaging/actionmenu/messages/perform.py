"""Represents a request to perform a menu action."""

from typing import Mapping

from marshmallow import fields

from ...agent_message import AgentMessage, AgentMessageSchema
from ..message_types import PERFORM

HANDLER_CLASS = (
    "aries_cloudagent.messaging.actionmenu.handlers.perform_handler.PerformHandler"
)


class Perform(AgentMessage):
    """Class representing a request to perform a menu action."""

    class Meta:
        """Perform metadata."""

        handler_class = HANDLER_CLASS
        message_type = PERFORM
        schema_class = "PerformSchema"

    def __init__(self, *, name: str = None, params: Mapping[str, str] = None, **kwargs):
        """
        Initialize a Perform object.

        Args:
            name: The name of the menu option
            params: Input parameter values
        """
        super(Perform, self).__init__(**kwargs)
        self.name = name
        self.params = params


class PerformSchema(AgentMessageSchema):
    """Perform schema class."""

    class Meta:
        """Perform schema metadata."""

        model_class = Perform

    name = fields.Str(required=True)
    params = fields.Dict(fields.Str(), fields.Str(), required=False)
