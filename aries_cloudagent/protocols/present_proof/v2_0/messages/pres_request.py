"""A presentation request content message."""

from typing import Sequence

from marshmallow import EXCLUDE, fields, validates_schema, ValidationError

from .....messaging.agent_message import AgentMessage, AgentMessageSchema
from .....messaging.decorators.attach_decorator import (
    AttachDecorator,
    AttachDecoratorSchema,
)

from ..message_types import PRES_20_REQUEST, PROTOCOL_PACKAGE

from .pres_format import V20PresFormat, V20PresFormatSchema

HANDLER_CLASS = (
    f"{PROTOCOL_PACKAGE}.handlers.pres_request_handler.V20PresRequestHandler"
)


class V20PresRequest(AgentMessage):
    """Class representing a presentation request."""

    class Meta:
        """V20PresRequest metadata."""

        handler_class = HANDLER_CLASS
        schema_class = "V20PresRequestSchema"
        message_type = PRES_20_REQUEST

    def __init__(
        self,
        _id: str = None,
        *,
        comment: str = None,
        will_confirm: bool = None,
        formats: Sequence[V20PresFormat] = None,
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
        self.will_confirm = will_confirm or False
        self.formats = list(formats) if formats else []
        self.request_presentations_attach = (
            list(request_presentations_attach) if request_presentations_attach else []
        )

    def attachment(self, fmt: V20PresFormat.Format = None) -> dict:
        """
        Return attached presentation request item.

        Args:
            fmt: format of attachment in list to decode and return

        """
        return (
            (fmt or V20PresFormat.Format.get(self.formats[0])).get_attachment_data(
                self.formats,
                self.request_presentations_attach,
            )
            if self.formats
            else None
        )


class V20PresRequestSchema(AgentMessageSchema):
    """Presentation request schema."""

    class Meta:
        """V20PresRequest schema metadata."""

        model_class = V20PresRequest
        unknown = EXCLUDE

    comment = fields.Str(required=False, description="Human-readable comment")
    will_confirm = fields.Bool(
        required=False, description="Whether verifier will send confirmation ack"
    )
    formats = fields.Nested(
        V20PresFormatSchema,
        many=True,
        required=True,
        descrption="Acceptable attachment formats",
    )
    request_presentations_attach = fields.Nested(
        AttachDecoratorSchema,
        many=True,
        required=True,
        description="Attachment per acceptable format on corresponding identifier",
        data_key="request_presentations~attach",
    )

    @validates_schema
    def validate_fields(self, data, **kwargs):
        """Validate attachment per format."""

        def get_attach_by_id(attach_id):
            """Return attachment with input attachment identifier."""
            for a in request_presentations_attach:
                if a.ident == attach_id:
                    return a
            raise ValidationError(
                f"No attachment matches attach_id {attach_id} in format"
            )

        formats = data.get("formats") or []
        request_presentations_attach = data.get("request_presentations_attach") or []
        if len(formats) != len(request_presentations_attach):
            raise ValidationError("Formats vs. attachments length mismatch")

        for fmt in formats:
            request_atch = get_attach_by_id(fmt.attach_id)
            V20PresFormat.Format.get(fmt.format).validate_request_attach(
                request_atch.content
            )
