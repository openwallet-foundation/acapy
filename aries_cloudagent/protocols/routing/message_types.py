"""Message type identifiers for Routing."""

PROTOCOL_URI = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/routing/1.0"

FORWARD = f"{PROTOCOL_URI}/forward"

ROUTE_QUERY_REQUEST = f"{PROTOCOL_URI}/route-query-request"
ROUTE_QUERY_RESPONSE = f"{PROTOCOL_URI}/route-query-response"
ROUTE_UPDATE_REQUEST = f"{PROTOCOL_URI}/route-update-request"
ROUTE_UPDATE_RESPONSE = f"{PROTOCOL_URI}/route-update-response"

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
}
