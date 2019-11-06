"""Message and inner object type identifiers for Connections."""

PROTOCOL_URI = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/issue-credential/1.0"

# Message types

CREDENTIAL_PROPOSAL = f"{PROTOCOL_URI}/propose-credential"
CREDENTIAL_OFFER = f"{PROTOCOL_URI}/offer-credential"
CREDENTIAL_REQUEST = f"{PROTOCOL_URI}/request-credential"
CREDENTIAL_ISSUE = f"{PROTOCOL_URI}/issue-credential"
CREDENTIAL_ACK = f"{PROTOCOL_URI}/ack"

PROTOCOL_PACKAGE = "aries_cloudagent.protocols.issue_credential.v1_0"

MESSAGE_TYPES = {
    CREDENTIAL_PROPOSAL: (
        f"{PROTOCOL_PACKAGE}.messages.credential_proposal.CredentialProposal"
    ),
    CREDENTIAL_OFFER: f"{PROTOCOL_PACKAGE}.messages.credential_offer.CredentialOffer",
    CREDENTIAL_REQUEST: (
        f"{PROTOCOL_PACKAGE}.messages.credential_request.CredentialRequest"
    ),
    CREDENTIAL_ISSUE: f"{PROTOCOL_PACKAGE}.messages.credential_issue.CredentialIssue",
    CREDENTIAL_ACK: (f"{PROTOCOL_PACKAGE}.messages.credential_ack.CredentialAck"),
}

# Inner object types
CREDENTIAL_PREVIEW = f"{PROTOCOL_URI}/credential-preview"

# Identifiers to use in attachment decorators
ATTACH_DECO_IDS = {
    CREDENTIAL_OFFER: "libindy-cred-offer-0",
    CREDENTIAL_REQUEST: "libindy-cred-request-0",
    CREDENTIAL_ISSUE: "libindy-cred-0",
}
