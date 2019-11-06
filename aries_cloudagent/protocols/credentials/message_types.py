"""Message type identifiers for credentials."""

PROTOCOL_URI = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/credential-issuance/0.1"

CREDENTIAL_OFFER = f"{PROTOCOL_URI}/credential-offer"
CREDENTIAL_REQUEST = f"{PROTOCOL_URI}/credential-request"
CREDENTIAL_ISSUE = f"{PROTOCOL_URI}/credential-issue"
CREDENTIAL_STORED = f"{PROTOCOL_URI}/credential-stored"

PROTOCOL_PACKAGE = "aries_cloudagent.protocols.credentials"

MESSAGE_TYPES = {
    CREDENTIAL_OFFER: f"{PROTOCOL_PACKAGE}.messages.credential_offer.CredentialOffer",
    CREDENTIAL_REQUEST: (
        f"{PROTOCOL_PACKAGE}.messages.credential_request.CredentialRequest"
    ),
    CREDENTIAL_ISSUE: f"{PROTOCOL_PACKAGE}.messages.credential_issue.CredentialIssue",
    CREDENTIAL_STORED: (
        f"{PROTOCOL_PACKAGE}.messages.credential_stored.CredentialStored"
    ),
}
