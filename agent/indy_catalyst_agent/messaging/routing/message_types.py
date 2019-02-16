"""
Message type identifiers for Connections
"""

MESSAGE_FAMILY = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/routing/1.0/"

CREATE_ROUTES = f"{MESSAGE_FAMILY}create"
DELETE_ROUTES = f"{MESSAGE_FAMILY}delete"
FORWARD = f"{MESSAGE_FAMILY}forward"
GET_ROUTES = f"{MESSAGE_FAMILY}get"
ROUTES = f"{MESSAGE_FAMILY}routes"

MESSAGE_PACKAGE = "indy_catalyst_agent.messaging.routing.messages"

MESSAGE_TYPES = {
    CREATE_ROUTES: f"{MESSAGE_PACKAGE}.create_routes.CreateRoutes",
    DELETE_ROUTES: f"{MESSAGE_PACKAGE}.delete_routes.DeleteRoutes",
    FORWARD: f"{MESSAGE_PACKAGE}.forward.Forward",
    GET_ROUTES: f"{MESSAGE_PACKAGE}.get_routes.GetRoutes",
    ROUTES: f"{MESSAGE_PACKAGE}.routes.Routes",
}
