"""Message type identifiers for Connections."""

from ...didcomm_prefix import DIDCommPrefix

SPEC_URI = (
    "https://github.com/hyperledger/aries-rfcs/tree/"
    "25464a5c8f8a17b14edaa4310393df6094ace7b0/features/0023-did-exchange"
)

# Message types
DIDEX_REQUEST = f"didexchange/1.0/request"
DIDEX_RESPONSE = f"didexchange/1.0/response"
DIDEX_COMPLETE = f"didexchange/1.0/complete"
PROBLEM_REPORT = f"didexchange/1.0/problem_report"

PROTOCOL_PACKAGE = "aries_cloudagent.protocols.didexchange.v1_0"

MESSAGE_TYPES = {
    **{
        pfx.qualify(DIDEX_REQUEST): (
            f"{PROTOCOL_PACKAGE}.messages.request.DIDExRequest"
        )
        for pfx in DIDCommPrefix
    },
    **{
        pfx.qualify(DIDEX_RESPONSE): (
            f"{PROTOCOL_PACKAGE}.messages.response.DIDExResponse"
        )
        for pfx in DIDCommPrefix
    },
    **{
        pfx.qualify(DIDEX_COMPLETE): (
            f"{PROTOCOL_PACKAGE}.messages.complete.DIDExComplete"
        )
        for pfx in DIDCommPrefix
    },
    **{
        pfx.qualify(PROBLEM_REPORT): (
            f"{PROTOCOL_PACKAGE}.messages.problem_report.ProblemReport"
        )
        for pfx in DIDCommPrefix
    },
}
