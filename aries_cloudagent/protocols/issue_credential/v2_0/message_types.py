"""Message and inner object type identifiers for Connections."""

from ...didcomm_prefix import DIDCommPrefix

from .messages.cred_format import V20CredFormat


SPEC_URI = (
    "https://github.com/hyperledger/aries-rfcs/tree/"
    "cd27fc64aa2805f756a118043d7c880354353047/features/0453-issue-credential-v2"
)

# Message types
CRED_20_PROPOSAL = "issue-credential/2.0/propose-credential"
CRED_20_OFFER = "issue-credential/2.0/offer-credential"
CRED_20_REQUEST = "issue-credential/2.0/request-credential"
CRED_20_ISSUE = "issue-credential/2.0/issue-credential"
CRED_20_ACK = "issue-credential/2.0/ack"
CRED_20_PROBLEM_REPORT = "issue-credential/2.0/problem-report"

PROTOCOL_PACKAGE = "aries_cloudagent.protocols.issue_credential.v2_0"

MESSAGE_TYPES = DIDCommPrefix.qualify_all(
    {
        CRED_20_PROPOSAL: (
            f"{PROTOCOL_PACKAGE}.messages.cred_proposal.V20CredProposal"
        ),
        CRED_20_OFFER: f"{PROTOCOL_PACKAGE}.messages.cred_offer.V20CredOffer",
        CRED_20_REQUEST: f"{PROTOCOL_PACKAGE}.messages.cred_request.V20CredRequest",
        CRED_20_ISSUE: f"{PROTOCOL_PACKAGE}.messages.cred_issue.V20CredIssue",
        CRED_20_ACK: f"{PROTOCOL_PACKAGE}.messages.cred_ack.V20CredAck",
        CRED_20_PROBLEM_REPORT: (
            f"{PROTOCOL_PACKAGE}.messages.cred_problem_report.V20CredProblemReport"
        ),
    }
)

# Inner object types
CRED_20_PREVIEW = "issue-credential/2.0/credential-preview"

# Format specifications
ATTACHMENT_FORMAT = {
    CRED_20_PROPOSAL: {
        V20CredFormat.Format.INDY.api: "hlindy/cred-filter@v2.0",
        V20CredFormat.Format.LD_PROOF.api: "aries/ld-proof-vc-detail@v1.0",
    },
    CRED_20_OFFER: {
        V20CredFormat.Format.INDY.api: "hlindy/cred-abstract@v2.0",
        V20CredFormat.Format.LD_PROOF.api: "aries/ld-proof-vc-detail@v1.0",
    },
    CRED_20_REQUEST: {
        V20CredFormat.Format.INDY.api: "hlindy/cred-req@v2.0",
        V20CredFormat.Format.LD_PROOF.api: "aries/ld-proof-vc-detail@v1.0",
    },
    CRED_20_ISSUE: {
        V20CredFormat.Format.INDY.api: "hlindy/cred@v2.0",
        V20CredFormat.Format.LD_PROOF.api: "aries/ld-proof-vc@v1.0",
    },
}

CONTROLLERS = DIDCommPrefix.qualify_all(
    {"issue-credential/2.0": f"{PROTOCOL_PACKAGE}.controller.Controller"}
)
