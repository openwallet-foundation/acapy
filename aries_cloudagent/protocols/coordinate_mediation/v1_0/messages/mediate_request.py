"""mediate-request message used to request mediation from a mediator."""

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

    def __init__(self, **kwargs):
        """Initialize mediation request object."""
        super(MediationRequest, self).__init__(**kwargs)


class MediationRequestSchema(AgentMessageSchema):
    """Mediation request schema class."""

    class Meta:
        """Mediation request schema metadata."""

        model_class = MediationRequest
