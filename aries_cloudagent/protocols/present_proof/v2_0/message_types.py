"""Message and inner object type identifiers for present-proof protocol v2.0."""

from ...didcomm_prefix import DIDCommPrefix

SPEC_URI = (
    "https://github.com/hyperledger/aries-rfcs/tree/"
    "de0092a41b7d54c4fe58a69e0dba24ae8bec9360/features/0454-present-proof-v2"
)

# Message types
PRES_20_PROPOSAL = "present-proof/2.0/propose-presentation"
PRES_20_REQUEST = "present-proof/2.0/request-presentation"
PRES_20 = "present-proof/2.0/presentation"
PRES_20_ACK = "present-proof/2.0/ack"

PROTOCOL_PACKAGE = "aries_cloudagent.protocols.present_proof.v2_0"

MESSAGE_TYPES = DIDCommPrefix.qualify_all(
    {
        PRES_PROPOSAL: (
            f"{PROTOCOL_PACKAGE}.messages.pres_proposal.PresProposal"
        ),
        PRES_REQUEST: (
            f"{PROTOCOL_PACKAGE}.messages.pres_request.PresRequest"
        ),
        PRES: f"{PROTOCOL_PACKAGE}.messages.pres.Pres",
        PRES_ACK: (
            f"{PROTOCOL_PACKAGE}.messages.pres_ack.PresAck"
        ),
    }
)

# Inner object types
PRES_20_PREVIEW = "present-proof/2.0/presentation-preview"
