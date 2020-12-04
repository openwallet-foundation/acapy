"""Represents a DID exchange complete message under RFC 23."""

from marshmallow import EXCLUDE, pre_dump, ValidationError

from .....messaging.agent_message import AgentMessage, AgentMessageSchema

from ..message_types import DIDX_COMPLETE, PROTOCOL_PACKAGE

HANDLER_CLASS = f"{PROTOCOL_PACKAGE}.handlers.complete_handler.DIDXCompleteHandler"


class DIDXComplete(AgentMessage):
    """Class representing a DID exchange completion."""

    class Meta:
        """Metadata for DID exchange completion."""

        handler_class = HANDLER_CLASS
        message_type = DIDX_COMPLETE
        schema_class = "DIDXCompleteSchema"

    def __init__(
        self,
        **kwargs,
    ):
        """Initialize DID exchange complete message object."""
        super().__init__(**kwargs)


class DIDXCompleteSchema(AgentMessageSchema):
    """DID exchange complete schema class."""

    class Meta:
        """DID exchange complete schema metadata."""

        model_class = DIDXComplete
        unknown = EXCLUDE

    @pre_dump
    def check_thread_deco(self, obj, **kwargs):
        """Thread decorator, and its thid and pthid, are mandatory."""
        if not obj._decorators.to_dict().get("~thread", {}).keys() >= {"thid", "pthid"}:
            raise ValidationError("Missing required field(s) in thread decorator")
        return obj
