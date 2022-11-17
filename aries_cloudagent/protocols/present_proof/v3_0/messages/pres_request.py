"""A presentation request content message."""

from typing import Sequence
from marshmallow import EXCLUDE, fields, validates_schema, ValidationError


from .....messaging.agent_message import AgentMessage, AgentMessageSchemaV2
from .....messaging.decorators.attach_decorator_didcomm_v2_pres import (
    AttachDecorator,
    AttachDecoratorSchema,
)

from ..message_types import PRES_30_REQUEST, PROTOCOL_PACKAGE

from .pres_format import V30PresFormat
from .pres_body import V30PresBody, V30PresBodySchema

HANDLER_CLASS = (
    f"{PROTOCOL_PACKAGE}.handlers.pres_request_handler.V30PresRequestHandler"
)


class V30PresRequest(AgentMessage):
    """Class representing a presentation request."""

    class Meta:
        """V30PresRequest metadata."""

        handler_class = HANDLER_CLASS
        schema_class = "V30PresRequestSchema"
        message_type = PRES_30_REQUEST

    def __init__(
        self,
        _id: str = None,
        *,
        body: V30PresBody = V30PresBody(),  # is REQUIRED in didcomv2
        attachments: Sequence[AttachDecorator] = None,
        **kwargs,
    ):
        """
        Initialize presentation request object.

        Args:
            attachments: proof request attachments
            comment: optional comment

        """
        super().__init__(_id=_id, **kwargs)

        self.body = body

        self.attachments = list(attachments) if attachments else []

    def attachment(self, fmt: V30PresFormat.Format = None) -> dict:
        """Return attachment or None if no attachments exists."""
        if len(self.attachments) != 0:
            for att in self.attachments:
                try:
                    if V30PresFormat.Format.get(att.format.format).api == fmt.api:
                        return att.content
                except AttributeError:
                    return None
        else:
            return None


class V30PresRequestSchema(AgentMessageSchemaV2):
    """Presentation request schema."""

    class Meta:
        """V30PresRequest schema metadata."""

        model_class = V30PresRequest
        unknown = EXCLUDE

    body = fields.Nested(
        V30PresBodySchema,  # including will_confirm
        comment="Human-readable comment",
        description="Body descriptor with GoalCode made for PresProof",
        data_key="body",
        example="hier könnt ihr body-example stehen",
        required=True,
        allow_none=False,
    )

    attachments = fields.Nested(
        AttachDecoratorSchema,
        many=True,
        required=False,
        description="Attachment per acceptable format on corresponding identifier",
        data_key="attachments",
    )

    @validates_schema
    def validate_fields(self, data, **kwargs):
        """Validate presentation attachment per format."""
        attachments = data.get("attachments") or []
        formats = []
        for atch in attachments:
            formats.append(atch.format)

        if len(formats) != len(attachments):
            raise ValidationError("Formats/attachments length mismatch")

        for atch in attachments:
            pres_format = V30PresFormat.Format.get(atch.format.format)
            if pres_format:
                pres_format.validate_fields(PRES_30_REQUEST, atch.content)
