"""mediate-deny message used to notify mediation client of a denied mediation request."""

from typing import Sequence

from marshmallow import fields

from .....messaging.agent_message import AgentMessage, AgentMessageSchema
from ..message_types import MEDIATE_DENY, PROTOCOL_PACKAGE

HANDLER_CLASS = (
    f"{PROTOCOL_PACKAGE}.handlers.mediation_deny_handler.MediationDenyHandler"
)


class MediationDeny(AgentMessage):
    """Class representing a mediation deny message."""

    class Meta:
        """Metadata for a mediation deny."""

        handler_class = HANDLER_CLASS
        message_type = MEDIATE_DENY
        schema_class = "MediationDenySchema"

    def __init__(
        self,
        *,
        mediator_terms: Sequence[str] = None,
        recipient_terms: Sequence[str] = None,
        **kwargs,
    ):
        """
        Initialize mediation deny object.

        Args:
            mediator_terms: Terms that were agreed by the recipient
            recipient_terms: Terms that recipient wants to mediator to agree to
        """
        super(MediationDeny, self).__init__(**kwargs)
        self.mediator_terms = list(mediator_terms) if mediator_terms else []
        self.recipient_terms = list(recipient_terms) if recipient_terms else []


class MediationDenySchema(AgentMessageSchema):
    """Mediation grant schema class."""

    class Meta:
        """Mediation deny schema metadata."""

        model_class = MediationDeny

    mediator_terms = fields.List(
        fields.Str(metadata={"description": "Terms for mediator to agree"}),
        required=False,
    )
    recipient_terms = fields.List(
        fields.Str(metadata={"description": "Terms for recipient to agree"}),
        required=False,
    )
