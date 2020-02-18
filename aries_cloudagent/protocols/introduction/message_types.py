"""Message type identifiers for Introductions."""

PROTOCOL_URI = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/introduction-service/0.1"

INVITATION_REQUEST = f"{PROTOCOL_URI}/invitation-request"
INVITATION = f"{PROTOCOL_URI}/invitation"
FORWARD_INVITATION = f"{PROTOCOL_URI}/forward-invitation"

NEW_PROTOCOL_URI = "https://didcomm.org/introduction-service/0.1"

NEW_INVITATION_REQUEST = f"{NEW_PROTOCOL_URI}/invitation-request"
NEW_INVITATION = f"{NEW_PROTOCOL_URI}/invitation"
NEW_FORWARD_INVITATION = f"{NEW_PROTOCOL_URI}/forward-invitation"

PROTOCOL_PACKAGE = "aries_cloudagent.protocols.introduction"

MESSAGE_TYPES = {
    INVITATION_REQUEST: (
        f"{PROTOCOL_PACKAGE}.messages.invitation_request.InvitationRequest"
    ),
    INVITATION: f"{PROTOCOL_PACKAGE}.messages.invitation.Invitation",
    FORWARD_INVITATION: (
        f"{PROTOCOL_PACKAGE}.messages.forward_invitation.ForwardInvitation"
    ),
    NEW_INVITATION_REQUEST: (
        f"{PROTOCOL_PACKAGE}.messages.invitation_request.InvitationRequest"
    ),
    NEW_INVITATION: f"{PROTOCOL_PACKAGE}.messages.invitation.Invitation",
    NEW_FORWARD_INVITATION: (
        f"{PROTOCOL_PACKAGE}.messages.forward_invitation.ForwardInvitation"
    ),
}
