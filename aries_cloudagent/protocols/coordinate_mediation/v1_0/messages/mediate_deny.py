"""mediate-deny message used to notify mediation client of a denied mediation request."""

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
        **kwargs,
    ):
        """Initialize mediation deny object."""
        super(MediationDeny, self).__init__(**kwargs)


class MediationDenySchema(AgentMessageSchema):
    """Mediation grant schema class."""

    class Meta:
        """Mediation deny schema metadata."""

        model_class = MediationDeny
