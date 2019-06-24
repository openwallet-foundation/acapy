"""Message type identifiers for Connections."""

MESSAGE_FAMILY = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/credential-issuance/0.1"

CREDENTIAL_OFFER = f"{MESSAGE_FAMILY}/credential-offer"
CREDENTIAL_REQUEST = f"{MESSAGE_FAMILY}/credential-request"
CREDENTIAL_ISSUE = f"{MESSAGE_FAMILY}/credential-issue"

MESSAGE_TYPES = {
    CREDENTIAL_OFFER: (
        "aries_cloudagent.messaging.credentials.messages."
        + "credential_offer.CredentialOffer"
    ),
    CREDENTIAL_REQUEST: (
        "aries_cloudagent.messaging.credentials.messages."
        + "credential_request.CredentialRequest"
    ),
    CREDENTIAL_ISSUE: (
        "aries_cloudagent.messaging.credentials.messages."
        + "credential_issue.CredentialIssue"
    ),
}
