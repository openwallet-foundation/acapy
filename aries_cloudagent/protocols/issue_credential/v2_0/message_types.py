"""Message and inner object type identifiers for Connections."""

from ...didcomm_prefix import DIDCommPrefix

SPEC_URI = (
    "https://github.com/hyperledger/aries-rfcs/tree/"
    "6509b84abaf5760a8ba1744c8078d513f28456db/features/0453-issue-credential-v2"
)

# Message types
CRED_20_PROPOSAL = "issue-credential/2.0/propose-credential"
CRED_20_OFFER = "issue-credential/2.0/offer-credential"
CRED_20_REQUEST = "issue-credential/2.0/request-credential"
CRED_20_ISSUE = "issue-credential/2.0/issue-credential"
CRED_20_ACK = "issue-credential/2.0/ack"

PROTOCOL_PACKAGE = "aries_cloudagent.protocols.issue_credential.v2_0"

MESSAGE_TYPES = DIDCommPrefix.qualify_all(
    {
        CRED_20_PROPOSAL: (
            f"{PROTOCOL_PACKAGE}.messages.cred_proposal.V20CredProposal"
        ),
        CRED_20_OFFER: (f"{PROTOCOL_PACKAGE}.messages.cred_offer.V20CredOffer"),
        CRED_20_REQUEST: (f"{PROTOCOL_PACKAGE}.messages.cred_request.V20CredRequest"),
        CRED_20_ISSUE: (f"{PROTOCOL_PACKAGE}.messages.cred_issue.V20CredIssue"),
        CRED_20_ACK: f"{PROTOCOL_PACKAGE}.messages.cred_ack.V20CredAck",
    }
)

# Inner object types
CRED_20_PREVIEW = "issue-credential/2.0/credential-preview"
