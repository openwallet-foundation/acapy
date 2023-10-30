"""Message type identifiers for Revocation Notification protocol."""

from ...didcomm_prefix import DIDCommPrefix


SPEC_URI = (
    "https://github.com/hyperledger/aries-rfcs/blob/main/features/"
    "0721-revocation-notification-v2/README.md"
)
PROTOCOL = "revocation_notification"
VERSION = "2.0"
BASE = f"{PROTOCOL}/{VERSION}"

# Message types
REVOKE = f"{BASE}/revoke"

PROTOCOL_PACKAGE = "aries_cloudagent.protocols.revocation_notification.v2_0"
MESSAGE_TYPES = DIDCommPrefix.qualify_all(
    {REVOKE: f"{PROTOCOL_PACKAGE}.messages.revoke.Revoke"}
)
