"""Enum representing captured send status of outbound messages."""

from enum import Enum

OUTBOUND_STATUS_PREFIX = "acapy::outbound-message::"


class OutboundSendStatus(Enum):
    """Send status of outbound messages."""

    # Could directly send the message to the connection over active session
    SENT_TO_SESSION = "sent_to_session"

    # Message is sent to external queue. We don't know how it will process the queue
    SENT_TO_EXTERNAL_QUEUE = "sent_to_external_queue"

    # Message is queued for delivery using outbound transport (recipient has endpoint)
    QUEUED_FOR_DELIVERY = "queued_for_delivery"

    # No endpoint available.
    # Need to wait for the recipient to connect with return routing for delivery
    WAITING_FOR_PICKUP = "waiting_for_pickup"

    # No endpoint available, and no internal queue for messages.
    UNDELIVERABLE = "undeliverable"

    @property
    def topic(self):
        """Return an event topic associated with a given status."""
        return f"{OUTBOUND_STATUS_PREFIX}{self.value}"
