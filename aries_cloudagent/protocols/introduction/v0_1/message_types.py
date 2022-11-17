"""Message type identifiers for Introductions."""

from ...didcomm_prefix import DIDCommPrefix

INVITATION_REQUEST = "introduction-service/0.1/invitation-request"
INVITATION = "introduction-service/0.1/invitation"
FORWARD_INVITATION = "introduction-service/0.1/forward-invitation"

PROTOCOL_PACKAGE = "aries_cloudagent.protocols.introduction.v0_1"

MESSAGE_TYPES = DIDCommPrefix.qualify_all(
    {
        INVITATION_REQUEST: (
            f"{PROTOCOL_PACKAGE}.messages.invitation_request.InvitationRequest"
        ),
        INVITATION: f"{PROTOCOL_PACKAGE}.messages.invitation.Invitation",
        FORWARD_INVITATION: (
            f"{PROTOCOL_PACKAGE}.messages.forward_invitation.ForwardInvitation"
        ),
    }
)
