"""Message type identifiers for Routing."""

from ...didcomm_prefix import DIDCommPrefix

# Message types
FORWARD = "routing/1.0/forward"

PROTOCOL_PACKAGE = "aries_cloudagent.protocols.routing.v1_0"

MESSAGE_TYPES = DIDCommPrefix.qualify_all(
    {
        FORWARD: f"{PROTOCOL_PACKAGE}.messages.forward.Forward",
    }
)
