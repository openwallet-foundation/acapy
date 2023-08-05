"""Credential proposal message."""

from typing import Sequence

from marshmallow import EXCLUDE, ValidationError, fields, validates_schema

from .....messaging.agent_message import AgentMessage, AgentMessageSchema
from .....messaging.decorators.attach_decorator import (
    AttachDecorator,
    AttachDecoratorSchema,
)
from ..message_types import CRED_20_PROPOSAL, PROTOCOL_PACKAGE
from .cred_format import V20CredFormat, V20CredFormatSchema
from .inner.cred_preview import V20CredPreview, V20CredPreviewSchema

HANDLER_CLASS = (
    f"{PROTOCOL_PACKAGE}.handlers.cred_proposal_handler.V20CredProposalHandler"
)


class V20CredProposal(AgentMessage):
    """Credential proposal."""

    class Meta:
        """V20CredProposal metadata."""

        handler_class = HANDLER_CLASS
        schema_class = "V20CredProposalSchema"
        message_type = CRED_20_PROPOSAL

    def __init__(
        self,
        _id: str = None,
        *,
        comment: str = None,
        credential_preview: V20CredPreview = None,
        formats: Sequence[V20CredFormat] = None,
        filters_attach: Sequence[AttachDecorator] = None,
        **kwargs,
    ):
        """
        Initialize credential proposal object.

        Args:
            comment: optional human-readable comment
            credential_proposal: proposed credential preview
            formats: acceptable attachment formats
            filters_attach: list of attachments filtering credential proposal

        """
        super().__init__(_id=_id, **kwargs)
        self.comment = comment
        self.credential_preview = credential_preview
        self.formats = list(formats) if formats else []
        self.filters_attach = list(filters_attach) if filters_attach else []

    def attachment(self, fmt: V20CredFormat.Format = None) -> dict:
        """
        Return attached filter.

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
            target_format.get_attachment_data(self.formats, self.filters_attach)
            if target_format
            else None
        )


class V20CredProposalSchema(AgentMessageSchema):
    """Credential proposal schema."""

    class Meta:
        """Credential proposal schema metadata."""

        model_class = V20CredProposal
        unknown = EXCLUDE

    comment = fields.Str(
        required=False,
        allow_none=True,
        metadata={"description": "Human-readable comment"},
    )
    credential_preview = fields.Nested(
        V20CredPreviewSchema,
        required=False,
        allow_none=False,
        metadata={"description": "Credential preview"},
    )
    formats = fields.Nested(
        V20CredFormatSchema,
        many=True,
        required=True,
        metadata={"description": "Attachment formats"},
    )
    filters_attach = fields.Nested(
        AttachDecoratorSchema,
        data_key="filters~attach",
        required=True,
        many=True,
        metadata={
            "description": (
                "Credential filter per acceptable format on corresponding identifier"
            )
        },
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
        attachments = data.get("filters_attach") or []
        if len(formats) != len(attachments):
            raise ValidationError("Formats/attachments length mismatch")

        for fmt in formats:
            atch = get_attach_by_id(fmt.attach_id)
            cred_format = V20CredFormat.Format.get(fmt.format)

            if cred_format:
                cred_format.validate_fields(CRED_20_PROPOSAL, atch.content)
