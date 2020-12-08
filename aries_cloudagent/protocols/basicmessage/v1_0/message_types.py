"""Message type identifiers for Connections."""

from ...didcomm_prefix import DIDCommPrefix

SPEC_URI = (
    "https://github.com/hyperledger/aries-rfcs/tree/"
    "527849ec3aa2a8fd47a7bb6c57f918ff8bcb5e8c/features/0095-basic-message"
)

# Message types
BASIC_MESSAGE = "basicmessage/1.0/message"

PROTOCOL_PACKAGE = "aries_cloudagent.protocols.basicmessage.v1_0"

MESSAGE_TYPES = DIDCommPrefix.qualify_all(
    {BASIC_MESSAGE: f"{PROTOCOL_PACKAGE}.messages.basicmessage.BasicMessage"}
)
