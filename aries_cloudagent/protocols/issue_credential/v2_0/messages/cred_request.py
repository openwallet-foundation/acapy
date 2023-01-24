"""Credential request message."""

from typing import Sequence

from marshmallow import EXCLUDE, fields, validates_schema, ValidationError

from .....messaging.agent_message import AgentMessage, AgentMessageSchema
from .....messaging.decorators.attach_decorator import (
    AttachDecorator,
    AttachDecoratorSchema,
)

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
        target_format = (
            fmt
            if fmt
            else next(
                filter(
                    lambda ff: ff,
                    [V20CredFormat.Format.get(f.format) for f in self.formats],
                ),
                None,
            )
        )
        return (
            target_format.get_attachment_data(self.formats, self.requests_attach)
            if target_format
            else None
        )

    def attachment_by_id(self, attach_id: str) -> dict:
        """
        Return attached credential request.

        Args:
            attach_id: string identifier

        """
        target_format = [
            V20CredFormat.Format.get(f.format)
            for f in self.formats
            if f.attach_id == attach_id
        ][0]
        return (
            target_format.get_attachment_data_by_id(attach_id, self.requests_attach)
            if target_format
            else None
        )

    def add_attachments(self, fmt: V20CredFormat, atch: AttachDecorator) -> None:
        """
        Update attachment format and requests attachment.

        Args:
            fmt: format of attachment
            atch: attachment
        """
        self.formats.append(fmt)
        self.requests_attach.append(atch)

    def add_formats(self, fmt_list: Sequence[V20CredFormat]) -> None:
        """
        Add format.

        Args:
            fmt_list: list of format attachment
        """
        for fmt in fmt_list:
            self.formats.append(fmt)

    def add_requests_attach(self, atch_list: Sequence[AttachDecorator]) -> None:
        """
        Add request_attach.

        Args:
            atch_list: list of attachment
        """
        for atch in atch_list:
            self.requests_attach.append(atch)


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
            cred_format = V20CredFormat.Format.get(fmt.format)

            if cred_format:
                cred_format.validate_fields(CRED_20_REQUEST, atch.content)
