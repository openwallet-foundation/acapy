"""Sane defaults for known message definitions."""

from .messaging.message_factory import MessageFactory

from .messaging.actionmenu.message_types import MESSAGE_TYPES as ACTIONMENU_MESSAGES
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


def default_message_factory() -> MessageFactory:
    """Message factory for default message types."""
    factory = MessageFactory()

    factory.register_message_types(
        ACTIONMENU_MESSAGES,
        BASICMESSAGE_MESSAGES,
        CONNECTION_MESSAGES,
        DISCOVERY_MESSAGES,
        INTRODUCTION_MESSAGES,
        PRESENTATION_MESSAGES,
        CREDENTIAL_MESSAGES,
        ROUTING_MESSAGES,
        TRUSTPING_MESSAGES,
    )

    return factory
