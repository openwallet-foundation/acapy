"""Message and inner object type identifiers for present-proof protocol v2.0."""

from ...didcomm_prefix import DIDCommPrefix

from .messages.pres_format import V20PresFormat

SPEC_URI = (
    "https://github.com/hyperledger/aries-rfcs/tree/"
    "eace815c3e8598d4a8dd7881d8c731fdb2bcc0aa/features/0454-present-proof-v2"
)

# Message types
PRES_20_PROPOSAL = "present-proof/2.0/propose-presentation"
PRES_20_REQUEST = "present-proof/2.0/request-presentation"
PRES_20 = "present-proof/2.0/presentation"
PRES_20_ACK = "present-proof/2.0/ack"
PRES_20_PROBLEM_REPORT = "present-proof/2.0/problem-report"

PROTOCOL_PACKAGE = "aries_cloudagent.protocols.present_proof.v2_0"

MESSAGE_TYPES = DIDCommPrefix.qualify_all(
    {
        PRES_20_PROPOSAL: f"{PROTOCOL_PACKAGE}.messages.pres_proposal.V20PresProposal",
        PRES_20_REQUEST: f"{PROTOCOL_PACKAGE}.messages.pres_request.V20PresRequest",
        PRES_20: f"{PROTOCOL_PACKAGE}.messages.pres.V20Pres",
        PRES_20_ACK: f"{PROTOCOL_PACKAGE}.messages.pres_ack.V20PresAck",
        PRES_20_PROBLEM_REPORT: (
            f"{PROTOCOL_PACKAGE}.messages.pres_problem_report.V20PresProblemReport"
        ),
    }
)

# Format specifications
ATTACHMENT_FORMAT = {
    PRES_20_PROPOSAL: {
        V20PresFormat.Format.INDY.api: "hlindy/proof-req@v2.0",
        V20PresFormat.Format.DIF.api: "dif/presentation-exchange/definitions@v1.0",
    },
    PRES_20_REQUEST: {
        V20PresFormat.Format.INDY.api: "hlindy/proof-req@v2.0",
        V20PresFormat.Format.DIF.api: "dif/presentation-exchange/definitions@v1.0",
    },
    PRES_20: {
        V20PresFormat.Format.INDY.api: "hlindy/proof@v2.0",
        V20PresFormat.Format.DIF.api: "dif/presentation-exchange/submission@v1.0",
    },
}

CONTROLLERS = DIDCommPrefix.qualify_all(
    {"present-proof/2.0": f"{PROTOCOL_PACKAGE}.controller.Controller"}
)
