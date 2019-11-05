"""Message type identifiers for Routing."""

PROTOCOL_URI = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/routing/1.0"

FORWARD = f"{PROTOCOL_URI}/forward"

ROUTE_QUERY_REQUEST = f"{PROTOCOL_URI}/route-query-request"
ROUTE_QUERY_RESPONSE = f"{PROTOCOL_URI}/route-query-response"
ROUTE_UPDATE_REQUEST = f"{PROTOCOL_URI}/route-update-request"
ROUTE_UPDATE_RESPONSE = f"{PROTOCOL_URI}/route-update-response"

NEW_PROTOCOL_URI = "https://didcomm.org/routing/1.0"

NEW_FORWARD = f"{NEW_PROTOCOL_URI}/forward"

NEW_ROUTE_QUERY_REQUEST = f"{NEW_PROTOCOL_URI}/route-query-request"
NEW_ROUTE_QUERY_RESPONSE = f"{NEW_PROTOCOL_URI}/route-query-response"
NEW_ROUTE_UPDATE_REQUEST = f"{NEW_PROTOCOL_URI}/route-update-request"
NEW_ROUTE_UPDATE_RESPONSE = f"{NEW_PROTOCOL_URI}/route-update-response"

PROTOCOL_PACKAGE = "aries_cloudagent.protocols.routing"

MESSAGE_TYPES = {
    FORWARD: f"{PROTOCOL_PACKAGE}.messages.forward.Forward",
    ROUTE_QUERY_REQUEST: (
        f"{PROTOCOL_PACKAGE}.messages.route_query_request.RouteQueryRequest"
    ),
    ROUTE_QUERY_RESPONSE: (
        f"{PROTOCOL_PACKAGE}.messages.route_query_response.RouteQueryResponse"
    ),
    ROUTE_UPDATE_REQUEST: (
        f"{PROTOCOL_PACKAGE}.messages.route_update_request.RouteUpdateRequest"
    ),
    ROUTE_UPDATE_RESPONSE: (
        f"{PROTOCOL_PACKAGE}.messages.route_update_response.RouteUpdateResponse"
    ),
    NEW_FORWARD: f"{PROTOCOL_PACKAGE}.messages.forward.Forward",
    NEW_ROUTE_QUERY_REQUEST: (
        f"{PROTOCOL_PACKAGE}.messages.route_query_request.RouteQueryRequest"
    ),
    NEW_ROUTE_QUERY_RESPONSE: (
        f"{PROTOCOL_PACKAGE}.messages.route_query_response.RouteQueryResponse"
    ),
    NEW_ROUTE_UPDATE_REQUEST: (
        f"{PROTOCOL_PACKAGE}.messages.route_update_request.RouteUpdateRequest"
    ),
    NEW_ROUTE_UPDATE_RESPONSE: (
        f"{PROTOCOL_PACKAGE}.messages.route_update_response.RouteUpdateResponse"
    ),
}
