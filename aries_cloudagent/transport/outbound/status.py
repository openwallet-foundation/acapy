"""Enum representing captured send status of outbound messages."""

from enum import Enum, auto


class OutboundSendStatus(Enum):
    """Send status of outbound messages."""

    SENT_TO_SESSION = auto()
    QUEUED_FOR_DELIVERY = auto()
