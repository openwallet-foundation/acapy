"""A presentation request content message."""

from typing import Sequence

from marshmallow import EXCLUDE, fields

from .....messaging.agent_message import AgentMessage, AgentMessageSchema
from .....messaging.decorators.attach_decorator import (
    AttachDecorator,
    AttachDecoratorSchema,
)

from ..message_types import PRESENTATION_REQUEST, PROTOCOL_PACKAGE

HANDLER_CLASS = (
    f"{PROTOCOL_PACKAGE}.handlers."
    "presentation_request_handler.PresentationRequestHandler"
)


class PresentationRequest(AgentMessage):
    """Class representing a presentation request."""

    class Meta:
        """PresentationRequest metadata."""

        handler_class = HANDLER_CLASS
        schema_class = "PresentationRequestSchema"
        message_type = PRESENTATION_REQUEST

    def __init__(
        self,
        _id: str = None,
        *,
        comment: str = None,
        request_presentations_attach: Sequence[AttachDecorator] = None,
        **kwargs,
    ):
        """
        Initialize presentation request object.

        Args:
            request_presentations_attach: proof request attachments
            comment: optional comment

        """
        super().__init__(_id=_id, **kwargs)
        self.comment = comment
        self.request_presentations_attach = (
            list(request_presentations_attach) if request_presentations_attach else []
        )

    def indy_proof_request(self, index: int = 0):
        """
        Retrieve and decode indy proof request from attachment.

        Args:
            index: ordinal in attachment list to decode and return
                (typically, list has length 1)

        """
        return self.request_presentations_attach[index].content


class PresentationRequestSchema(AgentMessageSchema):
    """Presentation request schema."""

    class Meta:
        """Presentation request schema metadata."""

        model_class = PresentationRequest
        unknown = EXCLUDE

    comment = fields.Str(
        description="Human-readable comment", required=False, allow_none=True
    )
    request_presentations_attach = fields.Nested(
        AttachDecoratorSchema,
        required=True,
        many=True,
        data_key="request_presentations~attach",
    )
