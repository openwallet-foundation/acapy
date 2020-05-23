"""Message type identifiers for Feature Discovery."""

SPEC_URI = (
    "https://github.com/hyperledger/aries-rfcs/tree/"
    "9b7ab9814f2e7d1108f74aca6f3d2e5d62899473/features/0031-discover-features"
)
PROTOCOL_URI = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/discover-features/1.0"

DISCLOSE = f"{PROTOCOL_URI}/disclose"
QUERY = f"{PROTOCOL_URI}/query"

NEW_PROTOCOL_URI = "https://didcomm.org/discover-features/1.0"

NEW_DISCLOSE = f"{NEW_PROTOCOL_URI}/disclose"
NEW_QUERY = f"{NEW_PROTOCOL_URI}/query"

PROTOCOL_PACKAGE = "aries_cloudagent.protocols.discovery.v1_0"

MESSAGE_TYPES = {
    DISCLOSE: f"{PROTOCOL_PACKAGE}.messages.disclose.Disclose",
    QUERY: f"{PROTOCOL_PACKAGE}.messages.query.Query",
    NEW_DISCLOSE: f"{PROTOCOL_PACKAGE}.messages.disclose.Disclose",
    NEW_QUERY: f"{PROTOCOL_PACKAGE}.messages.query.Query",
}
