"""Message and inner object type identifiers for Connections."""

from ...didcomm_prefix import DIDCommPrefix

SPEC_URI = (
    "https://github.com/hyperledger/aries-rfcs/tree/"
    "bb42a6c35e0d5543718fb36dd099551ab192f7b0/features/0036-issue-credential"
)

# Message types
CREDENTIAL_PROPOSAL = "issue-credential/1.0/propose-credential"
CREDENTIAL_OFFER = "issue-credential/1.0/offer-credential"
CREDENTIAL_REQUEST = "issue-credential/1.0/request-credential"
CREDENTIAL_ISSUE = "issue-credential/1.0/issue-credential"
CREDENTIAL_ACK = "issue-credential/1.0/ack"
CREDENTIAL_PROBLEM_REPORT = "issue-credential/1.0/problem-report"

PROTOCOL_PACKAGE = "aries_cloudagent.protocols.issue_credential.v1_0"

MESSAGE_TYPES = DIDCommPrefix.qualify_all(
    {
        CREDENTIAL_PROPOSAL: (
            f"{PROTOCOL_PACKAGE}.messages.credential_proposal.CredentialProposal"
        ),
        CREDENTIAL_OFFER: (
            f"{PROTOCOL_PACKAGE}.messages.credential_offer.CredentialOffer"
        ),
        CREDENTIAL_REQUEST: (
            f"{PROTOCOL_PACKAGE}.messages.credential_request.CredentialRequest"
        ),
        CREDENTIAL_ISSUE: (
            f"{PROTOCOL_PACKAGE}.messages.credential_issue.CredentialIssue"
        ),
        CREDENTIAL_ACK: f"{PROTOCOL_PACKAGE}.messages.credential_ack.CredentialAck",
        CREDENTIAL_PROBLEM_REPORT: (
            f"{PROTOCOL_PACKAGE}.messages.credential_problem_report."
            "CredentialProblemReport"
        ),
    }
)

# Inner object types
CREDENTIAL_PREVIEW = "issue-credential/1.0/credential-preview"

# Identifiers to use in attachment decorators
ATTACH_DECO_IDS = {
    CREDENTIAL_OFFER: "libindy-cred-offer-0",
    CREDENTIAL_REQUEST: "libindy-cred-request-0",
    CREDENTIAL_ISSUE: "libindy-cred-0",
}

CONTROLLERS = DIDCommPrefix.qualify_all(
    {"issue-credential/1.0": f"{PROTOCOL_PACKAGE}.controller.Controller"}
)
