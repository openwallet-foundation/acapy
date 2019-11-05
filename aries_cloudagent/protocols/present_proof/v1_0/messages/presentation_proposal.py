"""A presentation proposal content message."""

from marshmallow import fields

from .....messaging.agent_message import AgentMessage, AgentMessageSchema

from ..message_types import PRESENTATION_PROPOSAL, PROTOCOL_PACKAGE

from .inner.presentation_preview import PresentationPreview, PresentationPreviewSchema


HANDLER_CLASS = (
    f"{PROTOCOL_PACKAGE}.handlers."
    "presentation_proposal_handler.PresentationProposalHandler"
)


class PresentationProposal(AgentMessage):
    """Class representing a presentation proposal."""

    class Meta:
        """PresentationProposal metadata."""

        handler_class = HANDLER_CLASS
        schema_class = "PresentationProposalSchema"
        message_type = PRESENTATION_PROPOSAL

    def __init__(
        self,
        _id: str = None,
        *,
        comment: str = None,
        presentation_proposal: PresentationPreview = None,
        **kwargs,
    ):
        """
        Initialize presentation proposal object.

        Args:
            comment: optional human-readable comment
            presentation_proposal: proposed presentation preview
        """
        super().__init__(_id, **kwargs)
        self.comment = comment
        self.presentation_proposal = (
            presentation_proposal if presentation_proposal else PresentationPreview()
        )


class PresentationProposalSchema(AgentMessageSchema):
    """Presentation proposal schema."""

    class Meta:
        """Presentation proposal schema metadata."""

        model_class = PresentationProposal

    comment = fields.Str(description="Human-readable comment", required=False)
    presentation_proposal = fields.Nested(PresentationPreviewSchema, required=True)
