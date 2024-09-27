"""Message type identifiers for Feature Discovery."""

from ...didcomm_prefix import DIDCommPrefix

SPEC_URI = (
    "https://github.com/hyperledger/aries-rfcs/tree/"
    "b3a3942ef052039e73cd23d847f42947f8287da2/features/0557-discover-features-v2"
)

# Message types
DISCLOSURES = "discover-features/2.0/disclosures"
QUERIES = "discover-features/2.0/queries"

PROTOCOL_PACKAGE = "aries_cloudagent.protocols.discovery.v2_0"

MESSAGE_TYPES = DIDCommPrefix.qualify_all(
    {
        DISCLOSURES: f"{PROTOCOL_PACKAGE}.messages.disclosures.Disclosures",
        QUERIES: f"{PROTOCOL_PACKAGE}.messages.queries.Queries",
    }
)
