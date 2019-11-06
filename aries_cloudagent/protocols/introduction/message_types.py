"""Message type identifiers for Introductions."""

PROTOCOL_URI = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/introduction-service/0.1"

INVITATION_REQUEST = f"{PROTOCOL_URI}/invitation-request"
INVITATION = f"{PROTOCOL_URI}/invitation"
FORWARD_INVITATION = f"{PROTOCOL_URI}/forward-invitation"

PROTOCOL_PACKAGE = "aries_cloudagent.protocols.introduction"

MESSAGE_TYPES = {
    INVITATION_REQUEST: (
        f"{PROTOCOL_PACKAGE}.messages.invitation_request.InvitationRequest"
    ),
    INVITATION: f"{PROTOCOL_PACKAGE}.messages.invitation.Invitation",
    FORWARD_INVITATION: (
        f"{PROTOCOL_PACKAGE}.messages.forward_invitation.ForwardInvitation"
    ),
}
