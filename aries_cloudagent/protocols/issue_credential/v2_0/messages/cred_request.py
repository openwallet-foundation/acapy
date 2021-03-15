"""Credential request message."""

from typing import Sequence

from marshmallow import EXCLUDE, fields, RAISE, validates_schema, ValidationError

from .....messaging.agent_message import AgentMessage, AgentMessageSchema
from .....messaging.decorators.attach_decorator import (
    AttachDecorator,
    AttachDecoratorSchema,
)

from ...indy.cred_request import IndyCredRequestSchema

from ..message_types import CRED_20_REQUEST, PROTOCOL_PACKAGE

from .cred_format import V20CredFormat, V20CredFormatSchema

HANDLER_CLASS = (
    f"{PROTOCOL_PACKAGE}.handlers.cred_request_handler.V20CredRequestHandler"
)


class V20CredRequest(AgentMessage):
    """Credential request."""

    class Meta:
        """V20CredRequest metadata."""

        handler_class = HANDLER_CLASS
        schema_class = "V20CredRequestSchema"
        message_type = CRED_20_REQUEST

    def __init__(
        self,
        _id: str = None,
        *,
        comment: str = None,
        formats: Sequence[V20CredFormat] = None,
        requests_attach: Sequence[AttachDecorator] = None,
        **kwargs,
    ):
        """
        Initialize credential request object.

        Args:
            requests_attach: requests attachments
            comment: optional comment
            formats: acceptable attachment formats
            requests_attach: list of request attachments

        """
        super().__init__(_id=_id, **kwargs)
        self.comment = comment
        self.formats = list(formats) if formats else []
        self.requests_attach = list(requests_attach) if requests_attach else []

    def attachment(self, fmt: V20CredFormat.Format = None) -> dict:
        """
        Return attached credential request.

        Args:
            fmt: format of attachment in list to decode and return

        """
        return (
            (
                fmt or V20CredFormat.Format.get(self.formats[0].format)
            ).get_attachment_data(
                self.formats,
                self.requests_attach,
            )
            if self.formats
            else None
        )


class V20CredRequestSchema(AgentMessageSchema):
    """Credential request schema."""

    class Meta:
        """Credential request schema metadata."""

        model_class = V20CredRequest
        unknown = EXCLUDE

    comment = fields.Str(
        description="Human-readable comment", required=False, allow_none=True
    )
    formats = fields.Nested(
        V20CredFormatSchema,
        many=True,
        required=True,
        description="Acceptable attachment formats",
    )
    requests_attach = fields.Nested(
        AttachDecoratorSchema,
        required=True,
        many=True,
        data_key="requests~attach",
        description="Request attachments",
    )

    @validates_schema
    def validate_fields(self, data, **kwargs):
        """Validate attachments per format."""

        def get_attach_by_id(attach_id):
            """Return attachment with input identifier."""
            for atch in attachments:
                if atch.ident == attach_id:
                    return atch
            raise ValidationError(f"No attachment for attach_id {attach_id} in formats")

        formats = data.get("formats") or []
        attachments = data.get("requests_attach") or []
        if len(formats) != len(attachments):
            raise ValidationError("Formats/attachments length mismatch")

        for fmt in formats:
            atch = get_attach_by_id(fmt.attach_id)
            if V20CredFormat.Format.get(fmt.format) is V20CredFormat.Format.INDY:
                IndyCredRequestSchema(unknown=RAISE).load(atch.content)
