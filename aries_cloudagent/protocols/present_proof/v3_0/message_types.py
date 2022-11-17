"""Message and inner object type identifiers for present-proof protocol v3.0."""

from ...didcomm_prefix import DIDCommPrefix

from .messages.pres_format import V30PresFormat

SPEC_URI = (
    # there is not a rfc available for v3 now
    # Based on the link the attachment formats remain the same
    # https://github.com/decentralized-identity/waci-presentation-exchange/blob/main/present_proof/present-proof-v3.md
    "https://github.com/hyperledger/aries-rfcs/tree/"
    "eace815c3e8598d4a8dd7881d8c731fdb2bcc0aa/features/0454-present-proof-v3"
)

# Message types
PRES_30_PROPOSAL = "present-proof/3.0/propose-presentation"
PRES_30_REQUEST = "present-proof/3.0/request-presentation"
PRES_30 = "present-proof/3.0/presentation"
PRES_30_ACK = "present-proof/3.0/ack"
PRES_30_PROBLEM_REPORT = "present-proof/3.0/problem-report"

PROTOCOL_PACKAGE = "aries_cloudagent.protocols.present_proof.v3_0"

MESSAGE_TYPES = DIDCommPrefix.qualify_all(
    {
        PRES_30_PROPOSAL: f"{PROTOCOL_PACKAGE}.messages.pres_proposal.V30PresProposal",
        PRES_30_REQUEST: f"{PROTOCOL_PACKAGE}.messages.pres_request.V30PresRequest",
        PRES_30: f"{PROTOCOL_PACKAGE}.messages.pres.V30Pres",
        PRES_30_ACK: f"{PROTOCOL_PACKAGE}.messages.pres_ack.V30PresAck",
        PRES_30_PROBLEM_REPORT: (
            f"{PROTOCOL_PACKAGE}.messages.pres_problem_report.V30PresProblemReport"
        ),
    }
)

# Format specifications
ATTACHMENT_FORMAT = {
    PRES_30_PROPOSAL: {
        V30PresFormat.Format.INDY.api: "hlindy/proof-req@v3.0",
        V30PresFormat.Format.DIF.api: "dif/presentation-exchange/definitions@v1.0",
    },
    PRES_30_REQUEST: {
        V30PresFormat.Format.INDY.api: "hlindy/proof-req@v3.0",
        V30PresFormat.Format.DIF.api: "dif/presentation-exchange/definitions@v1.0",
    },
    PRES_30: {
        V30PresFormat.Format.INDY.api: "hlindy/proof@v3.0",
        V30PresFormat.Format.DIF.api: "dif/presentation-exchange/submission@v1.0",
    },
}

CONTROLLERS = DIDCommPrefix.qualify_all(
    {"present-proof/3.0": f"{PROTOCOL_PACKAGE}.controller.Controller"}
)
