"""Message type identifiers for Connections."""

from ....messaging.util import get_proto_default_version
from ...didcomm_prefix import DIDCommPrefix
from ..definition import versions

SPEC_URI = (
    "https://github.com/decentralized-identity/aries-rfcs/tree/"
    "25464a5c8f8a17b14edaa4310393df6094ace7b0/features/0023-did-exchange"
)
# Default Version
DEFAULT_VERSION = get_proto_default_version(versions, 1)
DIDEX_1_0 = "didexchange/1.0"
DIDEX_1_1 = "didexchange/1.1"
ARIES_PROTOCOL = f"didexchange/{DEFAULT_VERSION}"

# Message types
DIDX_REQUEST = f"{ARIES_PROTOCOL}/request"
DIDX_RESPONSE = f"{ARIES_PROTOCOL}/response"
DIDX_COMPLETE = f"{ARIES_PROTOCOL}/complete"
PROBLEM_REPORT = f"{ARIES_PROTOCOL}/problem_report"

PROTOCOL_PACKAGE = "acapy_agent.protocols.didexchange.v1_0"

MESSAGE_TYPES = DIDCommPrefix.qualify_all(
    {
        DIDX_REQUEST: f"{PROTOCOL_PACKAGE}.messages.request.DIDXRequest",
        DIDX_RESPONSE: f"{PROTOCOL_PACKAGE}.messages.response.DIDXResponse",
        DIDX_COMPLETE: f"{PROTOCOL_PACKAGE}.messages.complete.DIDXComplete",
        PROBLEM_REPORT: (f"{PROTOCOL_PACKAGE}.messages.problem_report.DIDXProblemReport"),
    }
)
