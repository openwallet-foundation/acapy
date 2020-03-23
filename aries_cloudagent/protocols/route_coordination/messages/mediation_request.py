"""A mediation request content message."""

from typing import Sequence

from marshmallow import fields

from ....messaging.agent_message import AgentMessage, AgentMessageSchema
from ..message_types import MEDIATION_REQUEST, PROTOCOL_PACKAGE

HANDLER_CLASS = (
    f"{PROTOCOL_PACKAGE}.handlers"
    ".mediaton_request_handler.MediationRequestHandler"
)


class MediationRequest(AgentMessage):
    """Class representing a mediation request."""

    class Meta:
        """Metadata for a mediation request."""

        handler_class = HANDLER_CLASS
        message_type = MEDIATION_REQUEST
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
            mediator_terms: Terms that were agreeed by the recipient
            recipient_terms: Terms that recipient wants to mediator to agree to
        """
        super(MediationRequest, self).__init__(**kwargs)
        self.mediator_terms = mediator_terms
        self.recipient_terms = recipient_terms


class MediationRequestSchema(AgentMessageSchema):
    """Mediation request schema class."""

    class Meta:
        """Mediation request schema metadata."""

        model_class = MediationRequest

    mediator_terms = fields.List(
        fields.Str(
            description="Indicate terms that the mediator "
            "requires the recipient to agree to"
        ),
        required=False,
        description="List of mediator rules for recipient",
    )
    recipient_terms = fields.List(
        fields.Str(
            description="Indicate terms that the recipient "
            "requires the mediator to agree to"
        ),
        required=False,
    )
