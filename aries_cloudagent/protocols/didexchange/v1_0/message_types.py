"""Message type identifiers for Connections."""

from ...didcomm_prefix import DIDCommPrefix

SPEC_URI = (
    "https://github.com/hyperledger/aries-rfcs/tree/"
    "25464a5c8f8a17b14edaa4310393df6094ace7b0/features/0023-did-exchange"
)
ARIES_PROTOCOL = "didexchange/1.0"

# Message types
DIDX_REQUEST = f"{ARIES_PROTOCOL}/request"
DIDX_RESPONSE = f"{ARIES_PROTOCOL}/response"
DIDX_COMPLETE = f"{ARIES_PROTOCOL}/complete"

PROTOCOL_PACKAGE = "aries_cloudagent.protocols.didexchange.v1_0"

MESSAGE_TYPES = DIDCommPrefix.qualify_all(
    {
        DIDX_REQUEST: f"{PROTOCOL_PACKAGE}.messages.request.DIDXRequest",
        DIDX_RESPONSE: f"{PROTOCOL_PACKAGE}.messages.response.DIDXResponse",
        DIDX_COMPLETE: f"{PROTOCOL_PACKAGE}.messages.complete.DIDXComplete",
    }
)
