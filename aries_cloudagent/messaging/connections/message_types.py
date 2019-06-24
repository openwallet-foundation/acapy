"""Message type identifiers for Connections."""

MESSAGE_FAMILY = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/connections/1.0"

CONNECTION_INVITATION = f"{MESSAGE_FAMILY}/invitation"
CONNECTION_REQUEST = f"{MESSAGE_FAMILY}/request"
CONNECTION_RESPONSE = f"{MESSAGE_FAMILY}/response"
PROBLEM_REPORT = f"{MESSAGE_FAMILY}/problem_report"

MESSAGE_TYPES = {
    CONNECTION_INVITATION: (
        "aries_cloudagent.messaging.connections.messages."
        + "connection_invitation.ConnectionInvitation"
    ),
    CONNECTION_REQUEST: (
        "aries_cloudagent.messaging.connections.messages."
        + "connection_request.ConnectionRequest"
    ),
    CONNECTION_RESPONSE: (
        "aries_cloudagent.messaging.connections.messages."
        + "connection_response.ConnectionResponse"
    ),
    PROBLEM_REPORT: (
        "aries_cloudagent.messaging.connections.messages."
        + "problem_report.ProblemReport"
    ),
}
