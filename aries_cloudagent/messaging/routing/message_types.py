"""Message type identifiers for Routing."""

MESSAGE_FAMILY = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/routing/1.0"

FORWARD = f"{MESSAGE_FAMILY}/forward"

ROUTE_QUERY_REQUEST = f"{MESSAGE_FAMILY}/route-query-request"
ROUTE_QUERY_RESPONSE = f"{MESSAGE_FAMILY}/route-query-response"
ROUTE_UPDATE_REQUEST = f"{MESSAGE_FAMILY}/route-update-request"
ROUTE_UPDATE_RESPONSE = f"{MESSAGE_FAMILY}/route-update-response"

MESSAGE_PACKAGE = "aries_cloudagent.messaging.routing.messages"

MESSAGE_TYPES = {
    FORWARD: f"{MESSAGE_PACKAGE}.forward.Forward",
    ROUTE_QUERY_REQUEST: f"{MESSAGE_PACKAGE}.route_query_request.RouteQueryRequest",
    ROUTE_QUERY_RESPONSE: f"{MESSAGE_PACKAGE}.route_query_response.RouteQueryResponse",
    ROUTE_UPDATE_REQUEST: f"{MESSAGE_PACKAGE}.route_update_request.RouteUpdateRequest",
    ROUTE_UPDATE_RESPONSE: (
        f"{MESSAGE_PACKAGE}.route_update_response.RouteUpdateResponse"
    ),
}
