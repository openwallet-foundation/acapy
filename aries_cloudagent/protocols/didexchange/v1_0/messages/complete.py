"""Represents a connection complete message under RFC 23 (DID exchange)."""

from marshmallow import EXCLUDE, fields, pre_dump, validates_schema, ValidationError

from .....messaging.agent_message import AgentMessage, AgentMessageSchema
from .....messaging.decorators.thread_decorator import (
    ThreadDecorator,
    ThreadDecoratorSchema,
)

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

    @pre_dump
    def check_thread_deco(self, obj, **kwargs):
        """Thread decorator, and its thid and pthid, are mandatory."""
        if not obj._decorators.to_dict().get("~thread", {}).keys() >= {"thid", "pthid"}:
            raise ValidationError("Missing required field(s) in thread decorator")
        return obj
