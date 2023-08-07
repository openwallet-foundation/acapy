"""A (proof) presentation content message."""

from typing import Sequence

from marshmallow import EXCLUDE, fields

from .....messaging.agent_message import AgentMessage, AgentMessageSchema
from .....messaging.decorators.attach_decorator import (
    AttachDecorator,
    AttachDecoratorSchema,
)
from ..message_types import PRESENTATION, PROTOCOL_PACKAGE

HANDLER_CLASS = f"{PROTOCOL_PACKAGE}.handlers.presentation_handler.PresentationHandler"


class Presentation(AgentMessage):
    """Class representing a (proof) presentation."""

    class Meta:
        """Presentation metadata."""

        handler_class = HANDLER_CLASS
        schema_class = "PresentationSchema"
        message_type = PRESENTATION

    def __init__(
        self,
        _id: str = None,
        *,
        comment: str = None,
        presentations_attach: Sequence[AttachDecorator] = None,
        **kwargs,
    ):
        """
        Initialize presentation object.

        Args:
            presentations_attach: attachments
            comment: optional comment

        """
        super().__init__(_id=_id, **kwargs)
        self.comment = comment
        self.presentations_attach = (
            list(presentations_attach) if presentations_attach else []
        )

    def indy_proof(self, index: int = 0):
        """
        Retrieve and decode indy proof from attachment.

        Args:
            index: ordinal in attachment list to decode and return
                (typically, list has length 1)

        """
        return self.presentations_attach[index].content


class PresentationSchema(AgentMessageSchema):
    """(Proof) presentation schema."""

    class Meta:
        """Presentation schema metadata."""

        model_class = Presentation
        unknown = EXCLUDE

    comment = fields.Str(
        required=False,
        allow_none=True,
        metadata={"description": "Human-readable comment"},
    )
    presentations_attach = fields.Nested(
        AttachDecoratorSchema, required=True, many=True, data_key="presentations~attach"
    )
