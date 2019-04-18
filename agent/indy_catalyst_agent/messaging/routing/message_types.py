"""Message type identifiers for Routing."""

MESSAGE_FAMILY = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/routing/1.0"

CREATE_ROUTES = f"{MESSAGE_FAMILY}/create"
DELETE_ROUTES = f"{MESSAGE_FAMILY}/delete"
FORWARD = f"{MESSAGE_FAMILY}/forward"
GET_ROUTES = f"{MESSAGE_FAMILY}/get"
ROUTES = f"{MESSAGE_FAMILY}/routes"

ROUTE_QUERY_REQUEST = f"{MESSAGE_FAMILY}route-query-request"
ROUTE_QUERY_RESPONSE = f"{MESSAGE_FAMILY}route-query-response"
ROUTE_UPDATE_REQUEST = f"{MESSAGE_FAMILY}route-update-request"
ROUTE_UPDATE_RESPONSE = f"{MESSAGE_FAMILY}route-update-response"

MESSAGE_PACKAGE = "indy_catalyst_agent.messaging.routing.messages"

MESSAGE_TYPES = {
    # CREATE_ROUTES: f"{MESSAGE_PACKAGE}.create_routes.CreateRoutes",
    # DELETE_ROUTES: f"{MESSAGE_PACKAGE}.delete_routes.DeleteRoutes",
    # FORWARD: f"{MESSAGE_PACKAGE}.forward.Forward",
    # GET_ROUTES: f"{MESSAGE_PACKAGE}.get_routes.GetRoutes",
    # ROUTES: f"{MESSAGE_PACKAGE}.routes.Routes",
    ROUTE_QUERY_REQUEST: f"{MESSAGE_PACKAGE}.route_query_request.RouteQueryRequest",
    ROUTE_QUERY_RESPONSE: f"{MESSAGE_PACKAGE}.route_query_response.RouteQueryResponse",
    ROUTE_UPDATE_REQUEST: f"{MESSAGE_PACKAGE}.route_update_request.RouteUpdateRequest",
    ROUTE_UPDATE_RESPONSE: f"{MESSAGE_PACKAGE}.route_update_request."
    "RouteUpdateResponse",
}
