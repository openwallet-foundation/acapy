"""A presentation request content message."""

from marshmallow import fields

from ....messaging.agent_message import AgentMessage, AgentMessageSchema

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
        message_type = PRESENTATION_REQUEST
        schema_class = "PresentationRequestSchema"

    def __init__(self, request: str = None, comment: str = None, **kwargs):
        """
        Initialize presentation request object.

        Args:
            request: Presentation request json string
        """
        super(PresentationRequest, self).__init__(**kwargs)
        self.request = request
        self.comment = comment


class PresentationRequestSchema(AgentMessageSchema):
    """PresentationRequest schema."""

    class Meta:
        """PresentationRequestSchema metadata."""

        model_class = PresentationRequest

    request = fields.Str(required=True)
    comment = fields.Str(required=False)
