"""Message type identifiers for Trust Pings."""

from ...didcomm_prefix import DIDCommPrefix

SPEC_URI = (
    "https://github.com/hyperledger/aries-rfcs/tree/"
    "527849ec3aa2a8fd47a7bb6c57f918ff8bcb5e8c/features/0048-trust-ping"
)

# Message types
PING = "trust_ping/1.0/ping"
PING_RESPONSE = "trust_ping/1.0/ping_response"

PROTOCOL_PACKAGE = "aries_cloudagent.protocols.trustping.v1_0"

MESSAGE_TYPES = DIDCommPrefix.qualify_all(
    {
        PING: f"{PROTOCOL_PACKAGE}.messages.ping.Ping",
        PING_RESPONSE: f"{PROTOCOL_PACKAGE}.messages.ping_response.PingResponse",
    }
)
