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
            proposal_attach: proposal attachments specifying criteria by format
        """
        super().__init__(_id, **kwargs)
        self.comment = comment
        self.formats = formats
        self.proposal_attach = proposal_attach or []

    def attachment(self, fmt: V20PresFormat.Format = None) -> dict:
        """
        Return attached proposal item.

        Args:
            fmt: format of attachment in list to decode and return

        """
        return (fmt or V20PresFormat.Format.INDY).get_attachment_data(
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
        description="Human-readable comment", required=False
    )
    formats = fields.Nested(
        V20PresFormatSchema,
        many=True,
        required=True,
        descrption="Acceptable attachment formats",
    )
    proposal_attach = fields.Nested(
        AttachDecoratorSchema,
        data_key="proposal~attach",
        required=True,
        description="Attachment per acceptable format on corresponding identifier",
    )

    @validates_schema
    def validate_fields(self, data, **kwargs):
        """Validate proposal attachment per format."""

        def get_attach_by_id(attach_id):
            """Return attachment with input attachment identifier."""
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
            proposal_atch = get_attach_by_id(fmt.attach_id)
            V20PresFormat.Format.get(fmt.format).validate_proposal_attach(
                proposal_atch.indy_dict
            )
