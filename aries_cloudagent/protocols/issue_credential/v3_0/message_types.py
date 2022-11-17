"""Message and inner object type identifiers for Connections."""

from ...didcomm_prefix import DIDCommPrefix

from .messages.cred_format import V30CredFormat


SPEC_URI = "https://github.com/decentralized-identity/waci-presentation-exchange/tree\
/main/issue_credential"

# Message types
CRED_30_PROPOSAL = "issue-credential/3.0/propose-credential"
CRED_30_OFFER = "issue-credential/3.0/offer-credential"
CRED_30_REQUEST = "issue-credential/3.0/request-credential"
CRED_30_ISSUE = "issue-credential/3.0/issue-credential"
CRED_30_ACK = "issue-credential/3.0/ack"
CRED_30_PROBLEM_REPORT = "issue-credential/3.0/problem-report"

PROTOCOL_PACKAGE = "aries_cloudagent.protocols.issue_credential.v3_0"

MESSAGE_TYPES = DIDCommPrefix.qualify_all(
    {
        CRED_30_PROPOSAL: (
            f"{PROTOCOL_PACKAGE}.messages.cred_proposal.V30CredProposal"
        ),
        CRED_30_OFFER: f"{PROTOCOL_PACKAGE}.messages.cred_offer.V30CredOffer",
        CRED_30_REQUEST: f"{PROTOCOL_PACKAGE}.messages.cred_request.V30CredRequest",
        CRED_30_ISSUE: f"{PROTOCOL_PACKAGE}.messages.cred_issue.V30CredIssue",
        CRED_30_ACK: f"{PROTOCOL_PACKAGE}.messages.cred_ack.V30CredAck",
        CRED_30_PROBLEM_REPORT: (
            f"{PROTOCOL_PACKAGE}.messages.cred_problem_report.V30CredProblemReport"
        ),
    }
)

# Inner object types
CRED_30_PREVIEW = "issue-credential/3.0/credential-preview"

# Format specifications
ATTACHMENT_FORMAT = {
    CRED_30_PROPOSAL: {
        V30CredFormat.Format.INDY.api: "hlindy/cred-filter@v3.0",
        V30CredFormat.Format.LD_PROOF.api: "aries/ld-proof-vc-detail@v1.0",
    },
    CRED_30_OFFER: {
        V30CredFormat.Format.INDY.api: "hlindy/cred-abstract@v3.0",
        V30CredFormat.Format.LD_PROOF.api: "aries/ld-proof-vc-detail@v1.0",
    },
    CRED_30_REQUEST: {
        V30CredFormat.Format.INDY.api: "hlindy/cred-req@v3.0",
        V30CredFormat.Format.LD_PROOF.api: "aries/ld-proof-vc-detail@v1.0",
    },
    CRED_30_ISSUE: {
        V30CredFormat.Format.INDY.api: "hlindy/cred@v3.0",
        V30CredFormat.Format.LD_PROOF.api: "aries/ld-proof-vc@v1.0",
    },
}

CONTROLLERS = DIDCommPrefix.qualify_all(
    {"issue-credential/3.0": f"{PROTOCOL_PACKAGE}.controller.Controller"}
)
