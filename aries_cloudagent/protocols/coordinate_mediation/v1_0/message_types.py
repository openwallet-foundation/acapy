"""Message type identifiers for Coordinate Mediation protocol."""

from ...didcomm_prefix import DIDCommPrefix

SPEC_URI = (
    "https://github.com/hyperledger/aries-rfcs/tree/"
    "fa8dc4ea1e667eb07db8f9ffeaf074a4455697c0/features/0211-route-coordination"
)

PROTOCOL = "coordinate-mediation"
VERSION = "1.0"
BASE = f"{PROTOCOL}/{VERSION}"

# Message types
MEDIATE_REQUEST = f"{BASE}/mediate-request"
MEDIATE_DENY = f"{BASE}/mediate-deny"
MEDIATE_GRANT = f"{BASE}/mediate-grant"
KEYLIST_UPDATE = f"{BASE}/keylist-update"
KEYLIST_UPDATE_RESPONSE = f"{BASE}/keylist-update-response"
KEYLIST_QUERY = f"{BASE}/keylist-query"
KEYLIST = f"{BASE}/keylist"
PROBLEM_REPORT = f"{BASE}/problem-report"

PROTOCOL_PACKAGE = "aries_cloudagent.protocols.coordinate_mediation.v1_0"

MESSAGE_TYPES = DIDCommPrefix.qualify_all(
    {
        KEYLIST: f"{PROTOCOL_PACKAGE}.messages.keylist.Keylist",
        KEYLIST_QUERY: f"{PROTOCOL_PACKAGE}.messages.keylist_query.KeylistQuery",
        KEYLIST_UPDATE: f"{PROTOCOL_PACKAGE}.messages.keylist_update.KeylistUpdate",
        KEYLIST_UPDATE_RESPONSE: (
            f"{PROTOCOL_PACKAGE}."
            "messages.keylist_update_response.KeylistUpdateResponse"
        ),
        MEDIATE_DENY: f"{PROTOCOL_PACKAGE}.messages.mediate_deny.MediationDeny",
        MEDIATE_GRANT: f"{PROTOCOL_PACKAGE}.messages.mediate_grant.MediationGrant",
        MEDIATE_REQUEST: (
            f"{PROTOCOL_PACKAGE}.messages.mediate_request.MediationRequest"
        ),
        PROBLEM_REPORT: f"{PROTOCOL_PACKAGE}.messages.problem_report.CMProblemReport",
    }
)

CONTROLLERS = DIDCommPrefix.qualify_all(
    {"coordinate-mediation/1.0": f"{PROTOCOL_PACKAGE}.controller.Controller"}
)
