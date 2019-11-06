"""Message type identifiers for presentations."""

PROTOCOL_URI = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/credential-presentation/0.1"

PRESENTATION_REQUEST = f"{PROTOCOL_URI}/presentation-request"
CREDENTIAL_PRESENTATION = f"{PROTOCOL_URI}/credential-presentation"

PROTOCOL_PACKAGE = "aries_cloudagent.protocols.presentations"

MESSAGE_TYPES = {
    PRESENTATION_REQUEST: (
        f"{PROTOCOL_PACKAGE}.messages.presentation_request.PresentationRequest"
    ),
    CREDENTIAL_PRESENTATION: (
        f"{PROTOCOL_PACKAGE}.messages.credential_presentation.CredentialPresentation"
    ),
}
