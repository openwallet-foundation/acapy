"""Sane defaults for known message definitions."""

from .messaging.protocol_registry import ProtocolRegistry

from .messaging.actionmenu.message_types import (
    CONTROLLERS as ACTIONMENU_CONTROLLERS,
    MESSAGE_TYPES as ACTIONMENU_MESSAGES,
)
from .messaging.basicmessage.message_types import MESSAGE_TYPES as BASICMESSAGE_MESSAGES
from .messaging.connections.message_types import MESSAGE_TYPES as CONNECTION_MESSAGES
from .messaging.discovery.message_types import MESSAGE_TYPES as DISCOVERY_MESSAGES
from .messaging.introduction.message_types import MESSAGE_TYPES as INTRODUCTION_MESSAGES
from .messaging.presentations.message_types import (
    MESSAGE_TYPES as PRESENTATION_MESSAGES,
)
from .messaging.credentials.message_types import MESSAGE_TYPES as CREDENTIAL_MESSAGES
from .messaging.trustping.message_types import MESSAGE_TYPES as TRUSTPING_MESSAGES
from .messaging.routing.message_types import MESSAGE_TYPES as ROUTING_MESSAGES

from .messaging.problem_report.message import (
    MESSAGE_TYPE as PROBLEM_REPORT,
    ProblemReport,
)


def default_protocol_registry() -> ProtocolRegistry:
    """Protocol registry for default message types."""
    registry = ProtocolRegistry()

    registry.register_message_types(
        ACTIONMENU_MESSAGES,
        BASICMESSAGE_MESSAGES,
        CONNECTION_MESSAGES,
        DISCOVERY_MESSAGES,
        INTRODUCTION_MESSAGES,
        PRESENTATION_MESSAGES,
        CREDENTIAL_MESSAGES,
        ROUTING_MESSAGES,
        TRUSTPING_MESSAGES,
        {PROBLEM_REPORT: ProblemReport},
    )

    registry.register_controllers(ACTIONMENU_CONTROLLERS)

    return registry
