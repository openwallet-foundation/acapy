"""A presentation proposal content message."""

from typing import Sequence

from marshmallow import EXCLUDE, fields, validates_schema, ValidationError

from .....messaging.agent_message import AgentMessage, AgentMessageSchema
from .....messaging.decorators.attach_decorator import (
    AttachDecorator,
    AttachDecoratorSchema,
)

from ..message_types import PRES_20_PROPOSAL, PROTOCOL_PACKAGE

from .pres_format import V20PresFormat, V20PresFormatSchema

HANDLER_CLASS = (
    f"{PROTOCOL_PACKAGE}.handlers.pres_proposal_handler.V20PresProposalHandler"
)


class V20PresProposal(AgentMessage):
    """Class representing a presentation proposal."""

    class Meta:
        """V20PresProposal metadata."""

        handler_class = HANDLER_CLASS
        schema_class = "V20PresProposalSchema"
        message_type = PRES_20_PROPOSAL

    def __init__(
        self,
        _id: str = None,
        *,
        comment: str = None,
        formats: Sequence[V20PresFormat],
        proposal_attach: Sequence[AttachDecorator],
        **kwargs,
    ):
        """
        Initialize pres proposal object.

        Args:
            comment: optional human-readable comment
            formats: acceptable attachment formats
            pres_proposal: proposed pres preview
        """
        super().__init__(_id, **kwargs)
        self.comment = comment
        self.pres_proposal = pres_proposal

    def proposal(self, fmt: V20PredFormat.Format = None) -> dict:
        """
        Return attached proposal item.

        Args:
            fmt: format of attachment in list to decode and return

        """
        return (fmt or V20PredFormat.Format.INDY).get_attachment_data(
            self.formats,
            self.proposal_attach,
        )

class V20PresProposalSchema(AgentMessageSchema):
    """Presentation proposal schema."""

    class Meta:
        """Presentation proposal schema metadata."""

        model_class = V20PresProposal
        unknown = EXCLUDE

    comment = fields.Str(
        description="Human-readable comment", required=False, allow_none=True
    )
    formats = fields.Nested(
        V20PredFormatSchema,
        many=True,
        required=True,
        descrption="Acceptable attachment formats",
    )
    proposal_attach = fields.Nested(
        AttachDecoratorSchema,
        data_key="filters~attach",
        required=True,
        description="Attachment per acceptable format on corresponding identifier",
    )

    @validates_schema
    def validate_fields(self, data, **kwargs):
        """Validate filter per format."""

        def get_proposal_attach_by_id(attach_id):
            """Return filter with input attachment identifier."""
            for p in proposal_attach:
                if p.ident == attach_id:
                    return p
            raise ValidationError(
                f"No proposal attachment matches attach_id {attach_id} in format"
            )

        formats = data.get("formats") or []
        proposal_attach = data.get("proposal_attach") or []
        if len(formats) != len(proposal_attach):
            raise ValidationError("Formats vs. proposal attachments length mismatch")

        for fmt in formats:
            proposal_atch = get_proposal_attach_by_id(fmt.attach_id)
            V20PresFormat.Format.get(fmt.format).validate_proposal_attach(
                proposal_atch.indy_dict
            )
