"""Message type identifiers for Trust Pings."""

#from ...didcomm_prefix import DIDCommPrefix

SPEC_URI = (
    "https://github.com/hyperledger/aries-rfcs/tree/"
    "527849ec3aa2a8fd47a7bb6c57f918ff8bcb5e8c/features/0048-trust-ping"
)

# Message types
PING = "trust_ping/1.0/ping"
PING_RESPONSE = "trust_ping/1.0/ping_response"
DEBUG = "https://didcomm.org/basicmessage/2.0/message"

PROTOCOL_PACKAGE = "acapy_agent.protocols.trustping.v1_0"

def test_func(context, responder, payload):
    message = payload
    print(message)

HANDLERS = {
    DEBUG: f"{PROTOCOL_PACKAGE}.message_types.test_func",
}.items()

MESSAGE_TYPES = {
        DEBUG: f"{PROTOCOL_PACKAGE}.message_types.test_func",
}
