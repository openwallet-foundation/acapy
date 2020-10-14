"""Represents a connection complete message under RFC 23 (DID exchange)."""

from marshmallow import EXCLUDE, validates_schema, ValidationError

from .....messaging.agent_message import AgentMessage, AgentMessageSchema

from ..message_types import CONN23_COMPLETE, PROTOCOL_PACKAGE

HANDLER_CLASS = f"{PROTOCOL_PACKAGE}.handlers.complete_handler.Conn23CompleteHandler"


class Conn23Complete(AgentMessage):
    """Class representing a connection completion."""

    class Meta:
        """Metadata for connection completion."""

        handler_class = HANDLER_CLASS
        message_type = CONN23_COMPLETE
        schema_class = "Conn23CompleteSchema"

    def __init__(
        self,
        *,
        **kwargs,
    ):
        """
        Initialize connection complete message object.

        """
        super().__init__(**kwargs)


class Conn23CompleteSchema(AgentMessageSchema):
    """Connection complete schema class."""

    class Meta:
        """Connection complete schema metadata."""

        model_class = Conn23Complete
        unknown = EXCLUDE

    @validates_schema
    def validate_fields(self, data, **kwargs):
        """
        Validate schema fields (thread deco thid, pthid are required here).

        Args:
            data: The data to validate

        Raises:
            ValidationError: If any of the fields do not validate

        """
        thread_deco = data.get("~thread", {})
        if not (("thid" in thread_deco) and ("pthid" in thread_deco)):
            raise ValidationError("Missing required field(s) in thread decorator")
