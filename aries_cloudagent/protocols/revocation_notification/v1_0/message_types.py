"""Message type identifiers for Revocation Notification protocol."""

from ...didcomm_prefix import DIDCommPrefix


SPEC_URI = (
    "https://github.com/hyperledger/aries-rfcs/blob/main/features/"
    "0183-revocation-notification/README.md"
)
PROTOCOL = "revocation_notification"
VERSION = "1.0"
BASE = f"{PROTOCOL}/{VERSION}"

# Message types
REVOKE = f"{BASE}/revoke"

PROTOCOL_PACKAGE = "aries_cloudagent.protocols.revocation_notification.v1_0"
MESSAGE_TYPES = DIDCommPrefix.qualify_all(
    {REVOKE: f"{PROTOCOL_PACKAGE}.messages.revoke.Revoke"}
)
