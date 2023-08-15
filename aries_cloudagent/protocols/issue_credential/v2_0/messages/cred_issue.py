"""Credential issue message."""

from typing import Sequence

from marshmallow import EXCLUDE, ValidationError, fields, validates_schema

from .....messaging.agent_message import AgentMessage, AgentMessageSchema
from .....messaging.decorators.attach_decorator import (
    AttachDecorator,
    AttachDecoratorSchema,
)
from .....messaging.valid import UUID4_EXAMPLE
from ..message_types import CRED_20_ISSUE, PROTOCOL_PACKAGE
from .cred_format import V20CredFormat, V20CredFormatSchema

HANDLER_CLASS = f"{PROTOCOL_PACKAGE}.handlers.cred_issue_handler.V20CredIssueHandler"


class V20CredIssue(AgentMessage):
    """Credential issue message."""

    class Meta:
        """V20CredIssue metadata."""

        handler_class = HANDLER_CLASS
        schema_class = "V20CredIssueSchema"
        message_type = CRED_20_ISSUE

    def __init__(
        self,
        _id: str = None,
        *,
        replacement_id: str = None,
        comment: str = None,
        formats: Sequence[V20CredFormat] = None,
        credentials_attach: Sequence[AttachDecorator] = None,
        **kwargs,
    ):
        """
        Initialize credential issue object.

        Args:
            comment: optional comment
            credentials_attach: credentials attachments
            formats: acceptable attachment formats
            filter_attach: list of credential attachments

        """
        super().__init__(_id=_id, **kwargs)
        self.replacement_id = replacement_id
        self.comment = comment
        self.formats = list(formats) if formats else []
        self.credentials_attach = list(credentials_attach) if credentials_attach else []

    def attachment(self, fmt: V20CredFormat.Format = None) -> dict:
        """
        Return attached credential.

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
            target_format.get_attachment_data(self.formats, self.credentials_attach)
            if target_format
            else None
        )


class V20CredIssueSchema(AgentMessageSchema):
    """Credential issue schema."""

    class Meta:
        """Credential issue schema metadata."""

        model_class = V20CredIssue
        unknown = EXCLUDE

    replacement_id = fields.Str(
        required=False,
        allow_none=False,
        metadata={
            "description": (
                "Issuer-unique identifier to coordinate credential replacement"
            ),
            "example": UUID4_EXAMPLE,
        },
    )
    comment = fields.Str(
        required=False,
        allow_none=True,
        metadata={"description": "Human-readable comment"},
    )
    formats = fields.Nested(
        V20CredFormatSchema,
        many=True,
        required=True,
        metadata={"description": "Acceptable attachment formats"},
    )
    credentials_attach = fields.Nested(
        AttachDecoratorSchema,
        many=True,
        required=True,
        data_key="credentials~attach",
        metadata={"description": "Credential attachments"},
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
        attachments = data.get("credentials_attach") or []
        if len(formats) != len(attachments):
            raise ValidationError("Formats/attachments length mismatch")

        for fmt in formats:
            atch = get_attach_by_id(fmt.attach_id)
            cred_format = V20CredFormat.Format.get(fmt.format)

            if cred_format:
                cred_format.validate_fields(CRED_20_ISSUE, atch.content)
