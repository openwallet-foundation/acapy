"""Message type identifiers for Action Menus."""

PROTOCOL_URI = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/action-menu/1.0"

MENU = f"{PROTOCOL_URI}/menu"
MENU_REQUEST = f"{PROTOCOL_URI}/menu-request"
PERFORM = f"{PROTOCOL_URI}/perform"

PROTOCOL_PACKAGE = "aries_cloudagent.protocols.actionmenu"

MESSAGE_TYPES = {
    MENU: f"{PROTOCOL_PACKAGE}.messages.menu.Menu",
    MENU_REQUEST: (f"{PROTOCOL_PACKAGE}.messages.menu_request.MenuRequest"),
    PERFORM: f"{PROTOCOL_PACKAGE}.messages.perform.Perform",
}

CONTROLLERS = {PROTOCOL_URI: f"{PROTOCOL_PACKAGE}.controller.Controller"}
