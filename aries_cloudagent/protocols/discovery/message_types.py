"""Message type identifiers for Feature Discovery."""

PROTOCOL_URI = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/discover-features/1.0"

DISCLOSE = f"{PROTOCOL_URI}/disclose"
QUERY = f"{PROTOCOL_URI}/query"

NEW_PROTOCOL_URI = "https://didcomm.org/discover-features/1.0"

NEW_DISCLOSE = f"{NEW_PROTOCOL_URI}/disclose"
NEW_QUERY = f"{NEW_PROTOCOL_URI}/query"

PROTOCOL_PACKAGE = "aries_cloudagent.protocols.discovery"

MESSAGE_TYPES = {
    DISCLOSE: f"{PROTOCOL_PACKAGE}.messages.disclose.Disclose",
    QUERY: f"{PROTOCOL_PACKAGE}.messages.query.Query",
    NEW_DISCLOSE: f"{PROTOCOL_PACKAGE}.messages.disclose.Disclose",
    NEW_QUERY: f"{PROTOCOL_PACKAGE}.messages.query.Query",
}
