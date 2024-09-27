"""Message and inner object type identifiers for present-proof protocol v1.0."""

from ...didcomm_prefix import DIDCommPrefix

SPEC_URI = (
    "https://github.com/hyperledger/aries-rfcs/tree/"
    "4fae574c03f9f1013db30bf2c0c676b1122f7149/features/0037-present-proof"
)

# Message types
PRESENTATION_PROPOSAL = "present-proof/1.0/propose-presentation"
PRESENTATION_REQUEST = "present-proof/1.0/request-presentation"
PRESENTATION = "present-proof/1.0/presentation"
PRESENTATION_ACK = "present-proof/1.0/ack"
PRESENTATION_PROBLEM_REPORT = "present-proof/1.0/problem-report"

PROTOCOL_PACKAGE = "aries_cloudagent.protocols.present_proof.v1_0"

MESSAGE_TYPES = DIDCommPrefix.qualify_all(
    {
        PRESENTATION_PROPOSAL: (
            f"{PROTOCOL_PACKAGE}.messages.presentation_proposal.PresentationProposal"
        ),
        PRESENTATION_REQUEST: (
            f"{PROTOCOL_PACKAGE}.messages.presentation_request.PresentationRequest"
        ),
        PRESENTATION: f"{PROTOCOL_PACKAGE}.messages.presentation.Presentation",
        PRESENTATION_ACK: (
            f"{PROTOCOL_PACKAGE}.messages.presentation_ack.PresentationAck"
        ),
        PRESENTATION_PROBLEM_REPORT: (
            f"{PROTOCOL_PACKAGE}.messages.presentation_problem_report."
            "PresentationProblemReport"
        ),
    }
)

# Identifiers to use in attachment decorators
ATTACH_DECO_IDS = {
    PRESENTATION_REQUEST: "libindy-request-presentation-0",
    PRESENTATION: "libindy-presentation-0",
}

CONTROLLERS = DIDCommPrefix.qualify_all(
    {"present-proof/1.0": f"{PROTOCOL_PACKAGE}.controller.Controller"}
)
