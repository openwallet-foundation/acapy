"""Message and inner object type identifiers for Connections."""

SPEC_URI = (
    "https://github.com/hyperledger/aries-rfcs/tree/"
    "bb42a6c35e0d5543718fb36dd099551ab192f7b0/features/0036-issue-credential"
)
PROTOCOL_URI = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/issue-credential/1.0"

# Message types

CREDENTIAL_PROPOSAL = f"{PROTOCOL_URI}/propose-credential"
CREDENTIAL_OFFER = f"{PROTOCOL_URI}/offer-credential"
CREDENTIAL_REQUEST = f"{PROTOCOL_URI}/request-credential"
CREDENTIAL_ISSUE = f"{PROTOCOL_URI}/issue-credential"
CREDENTIAL_ACK = f"{PROTOCOL_URI}/ack"

NEW_PROTOCOL_URI = "https://didcomm.org/issue-credential/1.0"

# Message types

NEW_CREDENTIAL_PROPOSAL = f"{NEW_PROTOCOL_URI}/propose-credential"
NEW_CREDENTIAL_OFFER = f"{NEW_PROTOCOL_URI}/offer-credential"
NEW_CREDENTIAL_REQUEST = f"{NEW_PROTOCOL_URI}/request-credential"
NEW_CREDENTIAL_ISSUE = f"{NEW_PROTOCOL_URI}/issue-credential"
NEW_CREDENTIAL_ACK = f"{NEW_PROTOCOL_URI}/ack"

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
    CREDENTIAL_ACK: f"{PROTOCOL_PACKAGE}.messages.credential_ack.CredentialAck",
    NEW_CREDENTIAL_PROPOSAL: (
        f"{PROTOCOL_PACKAGE}.messages.credential_proposal.CredentialProposal"
    ),
    NEW_CREDENTIAL_OFFER: (
        f"{PROTOCOL_PACKAGE}.messages.credential_offer.CredentialOffer"
    ),
    NEW_CREDENTIAL_REQUEST: (
        f"{PROTOCOL_PACKAGE}.messages.credential_request.CredentialRequest"
    ),
    NEW_CREDENTIAL_ISSUE: (
        f"{PROTOCOL_PACKAGE}.messages.credential_issue.CredentialIssue"
    ),
    NEW_CREDENTIAL_ACK: f"{PROTOCOL_PACKAGE}.messages.credential_ack.CredentialAck",
}

# Inner object types
CREDENTIAL_PREVIEW = f"{PROTOCOL_URI}/credential-preview"

# Identifiers to use in attachment decorators
ATTACH_DECO_IDS = {
    CREDENTIAL_OFFER: "libindy-cred-offer-0",
    CREDENTIAL_REQUEST: "libindy-cred-request-0",
    CREDENTIAL_ISSUE: "libindy-cred-0",
}
