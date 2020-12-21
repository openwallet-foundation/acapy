"""Message type identifiers for Connections."""

from ...didcomm_prefix import DIDCommPrefix

SPEC_URI = (
    "https://github.com/hyperledger/aries-rfcs/tree/"
    "9b0aaa39df7e8bd434126c4b33c097aae78d65bf/features/0160-connection-protocol"
)

# Message types
CONNECTION_INVITATION = "connections/1.0/invitation"
CONNECTION_REQUEST = "connections/1.0/request"
CONNECTION_RESPONSE = "connections/1.0/response"
TRANSACTION_ROLE_TO_SEND = "connections/1.0/transaction_my_role"
PROBLEM_REPORT = "connections/1.0/problem_report"

PROTOCOL_PACKAGE = "aries_cloudagent.protocols.connections.v1_0"

MESSAGE_TYPES = DIDCommPrefix.qualify_all(
    {
        CONNECTION_INVITATION: (
            f"{PROTOCOL_PACKAGE}.messages.connection_invitation.ConnectionInvitation"
        ),
        CONNECTION_REQUEST: (
            f"{PROTOCOL_PACKAGE}.messages.connection_request.ConnectionRequest"
        ),
        CONNECTION_RESPONSE: (
            f"{PROTOCOL_PACKAGE}.messages.connection_response.ConnectionResponse"
        ),
        TRANSACTION_ROLE_TO_SEND: (
            f"{PROTOCOL_PACKAGE}.messages.transaction_role_to_send.TransactionRoleToSend"
        ),
        PROBLEM_REPORT: f"{PROTOCOL_PACKAGE}.messages.problem_report.ProblemReport",
    }
)
