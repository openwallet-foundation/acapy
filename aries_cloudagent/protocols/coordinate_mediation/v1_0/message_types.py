"""Message type identifiers for Routing."""

from ...didcomm_prefix import DIDCommPrefix

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

PROTOCOL_PACKAGE = "aries_cloudagent.protocols.coordinate_mediation.v1_0"

MESSAGE_TYPES = {
    **{
        pfx.qualify(KEYLIST): f"{PROTOCOL_PACKAGE}.messages.keylist.Keylist"
        for pfx in DIDCommPrefix
    },
    **{
        pfx.qualify(KEYLIST_QUERY): f"{PROTOCOL_PACKAGE}."
        "messages.keylist_query.KeylistQuery"
        for pfx in DIDCommPrefix
    },
    **{
        pfx.qualify(KEYLIST_UPDATE): f"{PROTOCOL_PACKAGE}."
        "messages.keylist_update.KeylistUpdate"
        for pfx in DIDCommPrefix
    },
    **{
        pfx.qualify(KEYLIST_UPDATE_RESPONSE): f"{PROTOCOL_PACKAGE}."
        "messages.keylist_update_response.KeylistUpdateResponse"
        for pfx in DIDCommPrefix
    },
    **{
        pfx.qualify(MEDIATE_DENY): f"{PROTOCOL_PACKAGE}."
        "messages.mediate_deny.MediationDeny"
        for pfx in DIDCommPrefix
    },
    **{
        pfx.qualify(MEDIATE_GRANT): f"{PROTOCOL_PACKAGE}."
        "messages.mediate_grant.MediationGrant"
        for pfx in DIDCommPrefix
    },
    **{
        pfx.qualify(MEDIATE_REQUEST): f"{PROTOCOL_PACKAGE}."
        "messages.mediate_request.MediationRequest"
        for pfx in DIDCommPrefix
    },
}
