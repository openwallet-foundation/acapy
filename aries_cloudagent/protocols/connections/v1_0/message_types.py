"""Message type identifiers for Connections."""

SPEC_URI = (
    "https://github.com/hyperledger/aries-rfcs/tree/"
    "9b0aaa39df7e8bd434126c4b33c097aae78d65bf/features/0160-connection-protocol"
)
PROTOCOL_URI = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/connections/1.0"

CONNECTION_INVITATION = f"{PROTOCOL_URI}/invitation"
CONNECTION_REQUEST = f"{PROTOCOL_URI}/request"
CONNECTION_RESPONSE = f"{PROTOCOL_URI}/response"
PROBLEM_REPORT = f"{PROTOCOL_URI}/problem_report"

NEW_PROTOCOL_URI = "https://didcomm.org/connections/1.0"

NEW_CONNECTION_INVITATION = f"{NEW_PROTOCOL_URI}/invitation"
NEW_CONNECTION_REQUEST = f"{NEW_PROTOCOL_URI}/request"
NEW_CONNECTION_RESPONSE = f"{NEW_PROTOCOL_URI}/response"
NEW_PROBLEM_REPORT = f"{NEW_PROTOCOL_URI}/problem_report"

PROTOCOL_PACKAGE = "aries_cloudagent.protocols.connections.v1_0"

MESSAGE_TYPES = {
    CONNECTION_INVITATION: (
        f"{PROTOCOL_PACKAGE}.messages.connection_invitation.ConnectionInvitation"
    ),
    CONNECTION_REQUEST: (
        f"{PROTOCOL_PACKAGE}.messages.connection_request.ConnectionRequest"
    ),
    CONNECTION_RESPONSE: (
        f"{PROTOCOL_PACKAGE}.messages.connection_response.ConnectionResponse"
    ),
    PROBLEM_REPORT: f"{PROTOCOL_PACKAGE}.messages.problem_report.ProblemReport",
    NEW_CONNECTION_INVITATION: (
        f"{PROTOCOL_PACKAGE}.messages.connection_invitation.ConnectionInvitation"
    ),
    NEW_CONNECTION_REQUEST: (
        f"{PROTOCOL_PACKAGE}.messages.connection_request.ConnectionRequest"
    ),
    NEW_CONNECTION_RESPONSE: (
        f"{PROTOCOL_PACKAGE}.messages.connection_response.ConnectionResponse"
    ),
    NEW_PROBLEM_REPORT: f"{PROTOCOL_PACKAGE}.messages.problem_report.ProblemReport",
}
