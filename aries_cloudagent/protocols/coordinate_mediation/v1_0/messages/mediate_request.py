"""mediate-request message used to request mediation from a mediator."""

from typing import Sequence

from marshmallow import fields

from .....messaging.agent_message import AgentMessage, AgentMessageSchema
from ..message_types import MEDIATE_REQUEST, PROTOCOL_PACKAGE

HANDLER_CLASS = (
    f"{PROTOCOL_PACKAGE}.handlers.mediation_request_handler.MediationRequestHandler"
)


class MediationRequest(AgentMessage):
    """Represents a request for mediation."""

    class Meta:
        """MediationRequest metadata."""

        handler_class = HANDLER_CLASS
        message_type = MEDIATE_REQUEST
        schema_class = "MediationRequestSchema"

    def __init__(
        self,
        *,
        mediator_terms: Sequence[str] = None,
        recipient_terms: Sequence[str] = None,
        **kwargs,
    ):
        """
        Initialize mediation request object.

        Args:
            mediator_terms: Mediator's terms for granting mediation.
            recipient_terms: Recipient's proposed mediation terms.
        """
        super(MediationRequest, self).__init__(**kwargs)
        self.mediator_terms = list(mediator_terms) if mediator_terms else []
        self.recipient_terms = list(recipient_terms) if recipient_terms else []


class MediationRequestSchema(AgentMessageSchema):
    """Mediation request schema class."""

    class Meta:
        """Mediation request schema metadata."""

        model_class = MediationRequest

    mediator_terms = fields.List(
        fields.Str(
            metadata={
                "description": (
                    "Indicate terms that the mediator requires the recipient to"
                    " agree to"
                )
            }
        ),
        required=False,
        metadata={"description": "List of mediator rules for recipient"},
    )
    recipient_terms = fields.List(
        fields.Str(
            metadata={
                "description": (
                    "Indicate terms that the recipient requires the mediator to"
                    " agree to"
                )
            }
        ),
        required=False,
    )
