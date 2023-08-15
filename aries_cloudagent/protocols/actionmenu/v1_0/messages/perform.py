"""Represents a request to perform a menu action."""

from typing import Mapping

from marshmallow import EXCLUDE, fields

from .....messaging.agent_message import AgentMessage, AgentMessageSchema
from ..message_types import PERFORM, PROTOCOL_PACKAGE

HANDLER_CLASS = f"{PROTOCOL_PACKAGE}.handlers.perform_handler.PerformHandler"


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
        super().__init__(**kwargs)
        self.name = name
        self.params = params


class PerformSchema(AgentMessageSchema):
    """Perform schema class."""

    class Meta:
        """Perform schema metadata."""

        model_class = Perform
        unknown = EXCLUDE

    name = fields.Str(
        required=True, metadata={"description": "Menu option name", "example": "Query"}
    )
    params = fields.Dict(
        required=False,
        keys=fields.Str(metadata={"example": "parameter"}),
        values=fields.Str(metadata={"example": "value"}),
    )
