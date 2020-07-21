"""Message and inner object type identifiers for Out of Band messages."""

PROTOCOL_URI = "https://didcomm.org/out-of-band/1.0"

# New Message types

INVITATION = f"{PROTOCOL_URI}/invitation"

PROTOCOL_PACKAGE = "aries_cloudagent.protocols.out_of_band.v1_0"

MESSAGE_TYPES = {INVITATION: (f"{PROTOCOL_PACKAGE}.messages.invitation.Invitation")}
