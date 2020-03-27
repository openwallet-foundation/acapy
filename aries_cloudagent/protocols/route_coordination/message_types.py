"""Message and inner object type identifiers for route coordination protocol."""

PROTOCOL_URI = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/coordinatemediation/1.0/"

MEDIATION_REQUEST = f"{PROTOCOL_URI}/mediate-request"
MEDIATION_GRANT = f"{PROTOCOL_URI}/mediate-grant"
MEDIATION_DENY = f"{PROTOCOL_URI}/mediate-deny"
KEYLIST_UPDATE = f"{PROTOCOL_URI}/keylist_update"
KEYLIST_UPDATE_RESPONSE = f"{PROTOCOL_URI}/keylist_update_response"
KEYLIST_QUERY = f"{PROTOCOL_URI}/key_list_query"
KEYLIST = f"{PROTOCOL_URI}/key_list"

NEW_PROTOCOL_URI = "https://didcomm.org/coordinatemediation/1.0"

NEW_MEDIATION_REQUEST = f"{NEW_PROTOCOL_URI}/mediate-request"
NEW_MEDIATION_GRANT = f"{NEW_PROTOCOL_URI}/mediate-grant"
NEW_MEDIATION_DENY = f"{NEW_PROTOCOL_URI}/mediate-deny"
NEW_KEYLIST_UPDATE = f"{NEW_PROTOCOL_URI}/keylist_update"
NEW_KEYLIST_UPDATE_RESPONSE = f"{NEW_PROTOCOL_URI}/keylist_update_response"
NEW_KEYLIST_QUERY = f"{NEW_PROTOCOL_URI}/key_list_query"
NEW_KEYLIST = f"{NEW_PROTOCOL_URI}/key_list"

PROTOCOL_PACKAGE = "aries_cloudagent.protocols.route_coordination"

MESSAGE_TYPES = {
    MEDIATION_REQUEST: (
        f"{PROTOCOL_PACKAGE}.messages.mediation_request.MediationRequest"
    ),
    NEW_MEDIATION_REQUEST: (
        f"{PROTOCOL_PACKAGE}.messages.mediation_request.MediationRequest"
    ),
    MEDIATION_GRANT: (
        f"{PROTOCOL_PACKAGE}.messages.mediation_grant.MediationGrant"
    ),
    NEW_MEDIATION_GRANT: (
        f"{PROTOCOL_PACKAGE}.messages.mediation_grant.MediationGrant"
    ),
    MEDIATION_DENY: (
        f"{PROTOCOL_PACKAGE}.messages.mediation_deny.MediationDeny"
    ),
    NEW_MEDIATION_DENY: (
        f"{PROTOCOL_PACKAGE}.messages.mediation_deny.MediationDeny"
    ),
    KEYLIST_UPDATE: (
        f"{PROTOCOL_PACKAGE}.messages.keylist_update_request.KeylistUpdateRequest"
    ),
    NEW_KEYLIST_UPDATE: (
        f"{PROTOCOL_PACKAGE}.messages.keylist_update_request.KeylistUpdateRequest"
    ),
    KEYLIST_UPDATE_RESPONSE: (
        f"{PROTOCOL_PACKAGE}.messages.keylist_update_response.KeylistUpdateResponse"
    ),
    NEW_KEYLIST_UPDATE_RESPONSE: (
        f"{PROTOCOL_PACKAGE}.messages.keylist_update_response.KeylistUpdateResponse"
    ),
    KEYLIST_QUERY: f"{PROTOCOL_PACKAGE}.messages.keylist_query.KeylistQuery",
    NEW_KEYLIST_QUERY: f"{PROTOCOL_PACKAGE}.messages.keylist_query.KeylistQuery",
    KEYLIST: f"{PROTOCOL_PACKAGE}.messages.keylist.KeylistQueryResponse",
    NEW_KEYLIST: f"{PROTOCOL_PACKAGE}.messages.keylist.KeylistQueryResponse",
}
