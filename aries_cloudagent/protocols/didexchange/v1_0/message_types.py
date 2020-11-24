"""Message type identifiers for Connections."""

from ...didcomm_prefix import DIDCommPrefix

SPEC_URI = (
    "https://github.com/hyperledger/aries-rfcs/tree/"
    "25464a5c8f8a17b14edaa4310393df6094ace7b0/features/0023-did-exchange"
)

# Message types
DIDX_REQUEST = "didexchange/1.0/request"
DIDX_RESPONSE = "didexchange/1.0/response"
DIDX_COMPLETE = "didexchange/1.0/complete"
PROBLEM_REPORT = "didexchange/1.0/problem_report"

PROTOCOL_PACKAGE = "aries_cloudagent.protocols.didexchange.v1_0"

MESSAGE_TYPES = DIDCommPrefix.qualify_all(
    {
        DIDX_REQUEST: f"{PROTOCOL_PACKAGE}.messages.request.DIDXRequest",
        DIDX_RESPONSE: f"{PROTOCOL_PACKAGE}.messages.response.DIDXResponse",
        DIDX_COMPLETE: f"{PROTOCOL_PACKAGE}.messages.complete.DIDXComplete",
        PROBLEM_REPORT: f"{PROTOCOL_PACKAGE}.messages.problem_report.ProblemReport",
    }
)
