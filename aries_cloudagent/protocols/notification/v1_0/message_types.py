"""Message and inner object type identifiers for present-proof protocol v2.0."""

from ...didcomm_prefix import DIDCommPrefix

SPEC_URI = (
    "https://github.com/hyperledger/aries-rfcs/tree/"
    "560ffd23361f16a01e34ccb7dcc908ec28c5ddb1/features/0015-acks"
)

# Message types
NOTIF_10_ACK = "notification/1.0/ack"

PROTOCOL_PACKAGE = "aries_cloudagent.protocols.notification.v1_0"

MESSAGE_TYPES = DIDCommPrefix.qualify_all(
    {
        NOTIF_10_ACK: f"{PROTOCOL_PACKAGE}.messages.ack.V10Ack",
    }
)
