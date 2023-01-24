"""Credential issue message."""

from typing import Sequence

from marshmallow import EXCLUDE, fields, validates_schema, ValidationError

from .....messaging.agent_message import AgentMessage, AgentMessageSchema
from .....messaging.decorators.attach_decorator import (
    AttachDecorator,
    AttachDecoratorSchema,
)
from .....messaging.valid import UUIDFour

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
        more_available: int = 0,
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
            more_available: count of verifiable credentials willing to issue

        """
        super().__init__(_id=_id, **kwargs)
        self.replacement_id = replacement_id
        self.comment = comment
        self.formats = list(formats) if formats else []
        self.credentials_attach = list(credentials_attach) if credentials_attach else []
        self.more_available = more_available

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

    def attachment_by_id(self, attach_id: str) -> dict:
        """
        Return attached credential by attach identifier.

        Args:
            attach_id: string identifier

        """
        target_format = [
            V20CredFormat.Format.get(f.format)
            for f in self.formats
            if f.attach_id == attach_id
        ][0]
        return (
            target_format.get_attachment_data_by_id(attach_id, self.credentials_attach)
            if target_format
            else None
        )

    def add_attachments(self, fmt: V20CredFormat, atch: AttachDecorator) -> None:
        """
        Update attachment format and cred issue attachment.

        Args:
            fmt: format of attachment
            atch: attachment
        """
        self.formats.append(fmt)
        self.credentials_attach.append(atch)

    def add_formats(self, fmt_list: Sequence[V20CredFormat]) -> None:
        """
        Add format.

        Args:
            fmt_list: list of format attachment
        """
        for fmt in fmt_list:
            self.formats.append(fmt)

    def add_credentials_attach(self, atch_list: Sequence[AttachDecorator]) -> None:
        """
        Add credentials_attach.

        Args:
            atch_list: list of attachment
        """
        for atch in atch_list:
            self.credentials_attach.append(atch)


class V20CredIssueSchema(AgentMessageSchema):
    """Credential issue schema."""

    class Meta:
        """Credential issue schema metadata."""

        model_class = V20CredIssue
        unknown = EXCLUDE

    replacement_id = fields.Str(
        description="Issuer-unique identifier to coordinate credential replacement",
        required=False,
        allow_none=False,
        example=UUIDFour.EXAMPLE,
    )
    comment = fields.Str(
        description="Human-readable comment", required=False, allow_none=True
    )
    more_available = fields.Int(
        description="Count of the verifiable credential type for the Holder that the Issuer is willing to issue",
        required=False,
        strict=True,
    )
    formats = fields.Nested(
        V20CredFormatSchema,
        many=True,
        required=True,
        description="Acceptable attachment formats",
    )
    credentials_attach = fields.Nested(
        AttachDecoratorSchema,
        many=True,
        required=True,
        data_key="credentials~attach",
        description="Credential attachments",
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
