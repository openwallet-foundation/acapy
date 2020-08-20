"""Message type identifiers for Connections."""

SPEC_URI = (
    "https://github.com/hyperledger/aries-rfcs/tree/"
    "527849ec3aa2a8fd47a7bb6c57f918ff8bcb5e8c/features/0095-basic-message"
)
PROTOCOL_URI = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/basicmessage/1.0"

BASIC_MESSAGE = f"{PROTOCOL_URI}/message"

NEW_PROTOCOL_URI = "https://didcomm.org/basicmessage/1.0"

NEW_BASIC_MESSAGE = f"{NEW_PROTOCOL_URI}/message"

PROTOCOL_PACKAGE = "aries_cloudagent.protocols.basicmessage.v1_0"

MESSAGE_TYPES = {
    BASIC_MESSAGE: f"{PROTOCOL_PACKAGE}.messages.basicmessage.BasicMessage",
    NEW_BASIC_MESSAGE: f"{PROTOCOL_PACKAGE}.messages.basicmessage.BasicMessage",
}
