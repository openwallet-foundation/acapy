"""Message type identifiers for Connections."""

MESSAGE_FAMILY = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/connections/1.0/"

CONNECTION_INVITATION = f"{MESSAGE_FAMILY}invitation"
CONNECTION_REQUEST = f"{MESSAGE_FAMILY}request"
CONNECTION_RESPONSE = f"{MESSAGE_FAMILY}response"

MESSAGE_TYPES = {
    CONNECTION_INVITATION: (
        "indy_catalyst_agent.messaging.connections.messages."
        + "connection_invitation.ConnectionInvitation"
    ),
    CONNECTION_REQUEST: (
        "indy_catalyst_agent.messaging.connections.messages."
        + "connection_request.ConnectionRequest"
    ),
    CONNECTION_RESPONSE: (
        "indy_catalyst_agent.messaging.connections.messages."
        + "connection_response.ConnectionResponse"
    ),
}
