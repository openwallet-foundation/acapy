"""Message and inner object type identifiers for Connections."""

MESSAGE_FAMILY = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/issue-credential/1.0/"

# Message types

CREDENTIAL_PROPOSAL = f"{MESSAGE_FAMILY}propose-credential"
CREDENTIAL_OFFER = f"{MESSAGE_FAMILY}offer-credential"
CREDENTIAL_REQUEST = f"{MESSAGE_FAMILY}request-credential"
CREDENTIAL_ISSUE = f"{MESSAGE_FAMILY}issue-credential"

TOP = "aries_cloudagent.messaging.issue_credential.v1_0"
MESSAGE_TYPES = {
    CREDENTIAL_PROPOSAL: f"{TOP}.messages.credential_proposal.CredentialProposal",
    CREDENTIAL_OFFER: f"{TOP}.messages.credential_offer.CredentialOffer",
    CREDENTIAL_REQUEST: f"{TOP}.messages.credential_request.CredentialRequest",
    CREDENTIAL_ISSUE: "{TOP}.messages.credential_issue.CredentialIssue"
}

# Inner object types
CREDENTIAL_PREVIEW = f"{MESSAGE_FAMILY}credential-preview"

INNER_OBJECT_TYPES = {
    CREDENTIAL_PREVIEW: f"{TOP}.credential_preview.CredentialPreview"
}
