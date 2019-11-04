"""Message type identifiers for Connections."""

PROTOCOL_URI = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/connections/1.0"

CONNECTION_INVITATION = f"{PROTOCOL_URI}/invitation"
CONNECTION_REQUEST = f"{PROTOCOL_URI}/request"
CONNECTION_RESPONSE = f"{PROTOCOL_URI}/response"
PROBLEM_REPORT = f"{PROTOCOL_URI}/problem_report"

PROTOCOL_PACKAGE = "aries_cloudagent.protocols.connections"

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
}
