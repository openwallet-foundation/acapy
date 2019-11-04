"""Message type identifiers for Feature Discovery."""

PROTOCOL_URI = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/discover-features/1.0"

DISCLOSE = f"{PROTOCOL_URI}/disclose"
QUERY = f"{PROTOCOL_URI}/query"

PROTOCOL_PACKAGE = "aries_cloudagent.protocols.discovery"

MESSAGE_TYPES = {
    DISCLOSE: f"{PROTOCOL_PACKAGE}.messages.disclose.Disclose",
    QUERY: f"{PROTOCOL_PACKAGE}.messages.query.Query",
}
