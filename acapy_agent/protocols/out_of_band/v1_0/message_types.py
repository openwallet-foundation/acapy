"""Message and inner object type identifiers for Out of Band messages."""

from ....messaging.util import get_proto_default_version
from ...didcomm_prefix import DIDCommPrefix
from ..definition import versions

SPEC_URI = (
    "https://github.com/decentralized-identity/aries-rfcs/tree/"
    "2da7fc4ee043effa3a9960150e7ba8c9a4628b68/features/0434-outofband"
)

# Default Version
DEFAULT_VERSION = get_proto_default_version(versions, 1)

# Message types
INVITATION = f"out-of-band/{DEFAULT_VERSION}/invitation"
MESSAGE_REUSE = f"out-of-band/{DEFAULT_VERSION}/handshake-reuse"
MESSAGE_REUSE_ACCEPT = f"out-of-band/{DEFAULT_VERSION}/handshake-reuse-accepted"
PROBLEM_REPORT = f"out-of-band/{DEFAULT_VERSION}/problem_report"


PROTOCOL_PACKAGE = "acapy_agent.protocols.out_of_band.v1_0"

MESSAGE_TYPES = DIDCommPrefix.qualify_all(
    {
        INVITATION: f"{PROTOCOL_PACKAGE}.messages.invitation.Invitation",
        MESSAGE_REUSE: f"{PROTOCOL_PACKAGE}.messages.reuse.HandshakeReuse",
        MESSAGE_REUSE_ACCEPT: (
            f"{PROTOCOL_PACKAGE}.messages.reuse_accept.HandshakeReuseAccept"
        ),
        PROBLEM_REPORT: f"{PROTOCOL_PACKAGE}.messages.problem_report.OOBProblemReport",
    }
)

CONTROLLERS = DIDCommPrefix.qualify_all(
    {"out-of-band/1.0": f"{PROTOCOL_PACKAGE}.controller.Controller"}
)
