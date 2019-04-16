"""Message type identifiers for Introductions."""

MESSAGE_FAMILY = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/introduction-service/0.1/"

INVITATION_REQUEST = f"{MESSAGE_FAMILY}invitation-request"
INVITATION = f"{MESSAGE_FAMILY}invitation"
FORWARD_INVITATION = f"{MESSAGE_FAMILY}forward-invitation"

MESSAGE_TYPES = {
    INVITATION_REQUEST: (
        "indy_catalyst_agent.messaging.introduction.messages."
        + "invitation_request.InvitationRequest"
    ),
    INVITATION: (
        "indy_catalyst_agent.messaging.introduction.messages.invitation.Invitation"
    ),
    FORWARD_INVITATION: (
        "indy_catalyst_agent.messaging.introduction.messages."
        + "forward_invitation.ForwardInvitation"
    ),
}
