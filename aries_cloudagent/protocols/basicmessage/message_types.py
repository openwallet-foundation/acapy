"""Message type identifiers for Connections."""

PROTOCOL_URI = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/basicmessage/1.0"

BASIC_MESSAGE = f"{PROTOCOL_URI}/message"

PROTOCOL_PACKAGE = "aries_cloudagent.protocols.basicmessage"

MESSAGE_TYPES = {
    BASIC_MESSAGE: f"{PROTOCOL_PACKAGE}.messages.basicmessage.BasicMessage"
}
