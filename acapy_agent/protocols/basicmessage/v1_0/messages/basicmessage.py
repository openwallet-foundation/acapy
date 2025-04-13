"""Basic message."""

from datetime import datetime
from typing import Optional, Union

from marshmallow import EXCLUDE, fields

from .....messaging.agent_message import AgentMessage, AgentMessageSchema
from .....messaging.util import datetime_now, datetime_to_str
from .....messaging.valid import ISO8601_DATETIME_EXAMPLE, ISO8601_DATETIME_VALIDATE
from ..message_types import BASIC_MESSAGE, PROTOCOL_PACKAGE

HANDLER_CLASS = f"{PROTOCOL_PACKAGE}.handlers.basicmessage_handler.BasicMessageHandler"


class BasicMessage(AgentMessage):
    """Class defining the structure of a basic message."""

    class Meta:
        """Basic message metadata class."""

        handler_class = HANDLER_CLASS
        message_type = BASIC_MESSAGE
        schema_class = "BasicMessageSchema"

    def __init__(
        self,
        *,
        sent_time: Union[str, datetime] = None,
        content: Optional[str] = None,
        localization: Optional[str] = None,
        **kwargs,
    ):
        """Initialize basic message object.

        Args:
            sent_time: Time message was sent
            content: message content
            localization: localization
            kwargs: additional keyword arguments

        """
        super().__init__(**kwargs)
        if not sent_time:
            sent_time = datetime_now()
        if localization:
            self._decorators["l10n"] = localization
        self.sent_time = datetime_to_str(sent_time)
        self.content = content


class BasicMessageSchema(AgentMessageSchema):
    """Basic message schema class."""

    class Meta:
        """Basic message schema metadata."""

        model_class = BasicMessage
        unknown = EXCLUDE

    sent_time = fields.Str(
        required=False,
        validate=ISO8601_DATETIME_VALIDATE,
        metadata={
            "description": (
                "Time message was sent, ISO8601 with space date/time separator"
            ),
            "example": ISO8601_DATETIME_EXAMPLE,
        },
    )
    content = fields.Str(
        required=True, metadata={"description": "Message content", "example": "Hello"}
    )
