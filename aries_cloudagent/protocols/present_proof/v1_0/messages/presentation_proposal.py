"""A presentation proposal content message."""

from marshmallow import EXCLUDE, fields

from .....messaging.agent_message import AgentMessage, AgentMessageSchema

from ..message_types import PRESENTATION_PROPOSAL, PROTOCOL_PACKAGE

from ...indy.presentation_preview import (
    IndyPresentationPreview,
    IndyPresentationPreviewSchema,
)

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
        presentation_proposal: IndyPresentationPreview = None,
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
        self.presentation_proposal = presentation_proposal


class PresentationProposalSchema(AgentMessageSchema):
    """Presentation proposal schema."""

    class Meta:
        """Presentation proposal schema metadata."""

        model_class = PresentationProposal
        unknown = EXCLUDE

    comment = fields.Str(
        description="Human-readable comment", required=False, allow_none=True
    )
    presentation_proposal = fields.Nested(IndyPresentationPreviewSchema, required=True)
