"""Credential proposal message."""

from typing import Sequence

from marshmallow import EXCLUDE, fields, validates_schema, ValidationError

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
            formats: acceptable credential formats
            filter_attach: list of attachments filtering credential proposal

        """
        super().__init__(_id=_id, **kwargs)
        self.comment = comment
        self.credential_preview = credential_preview
        self.formats = list(formats) if formats else []
        self.filters_attach = list(filters_attach) if filters_attach else []

    def filter(self, fmt: V20CredFormat.Format = None) -> dict:
        """
        Return attached filter.

        Args:
            fmt: format of attachment in list to decode and return

        """
        return (fmt or V20CredFormat.Format.INDY).get_attachment_data(
            self.formats,
            self.filters_attach,
        )


class V20CredProposalSchema(AgentMessageSchema):
    """Credential proposal schema."""

    class Meta:
        """Credential proposal schema metadata."""

        model_class = V20CredProposal
        unknown = EXCLUDE

    comment = fields.Str(
        description="Human-readable comment", required=False, allow_none=True
    )
    credential_preview = fields.Nested(
        V20CredPreviewSchema,
        description="Credential preview",
        required=False,
        allow_none=False,
    )
    formats = fields.Nested(
        V20CredFormatSchema,
        many=True,
        required=True,
        description="Acceptable credential formats",
    )
    filters_attach = fields.Nested(
        AttachDecoratorSchema,
        data_key="filters~attach",
        required=True,
        description=(
            "Credential filter per acceptable format " "on corresponding identifier"
        ),
        many=True,
    )

    @validates_schema
    def validate_fields(self, data, **kwargs):
        """Validate filter per format."""

        def get_filter_attach_by_id(attach_id):
            """Return filter with input attachment identifier."""
            for f in filters_attach:
                if f.ident == attach_id:
                    return f
            raise ValidationError(f"No filter matches attach_id {attach_id} in format")

        formats = data.get("formats") or []
        filters_attach = data.get("filters_attach") or []
        if len(formats) != len(filters_attach):
            raise ValidationError("Formats/filters length mismatch")

        for fmt in formats:
            filt_atch = get_filter_attach_by_id(fmt.attach_id)
            V20CredFormat.Format.get(fmt.format).validate_filter(filt_atch.content)
