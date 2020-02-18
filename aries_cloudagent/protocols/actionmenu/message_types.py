"""Message type identifiers for Action Menus."""

PROTOCOL_URI = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/action-menu/1.0"

MENU = f"{PROTOCOL_URI}/menu"
MENU_REQUEST = f"{PROTOCOL_URI}/menu-request"
PERFORM = f"{PROTOCOL_URI}/perform"

NEW_PROTOCOL_URI = "https://didcomm.org/action-menu/1.0"

NEW_MENU = f"{NEW_PROTOCOL_URI}/menu"
NEW_MENU_REQUEST = f"{NEW_PROTOCOL_URI}/menu-request"
NEW_PERFORM = f"{NEW_PROTOCOL_URI}/perform"

PROTOCOL_PACKAGE = "aries_cloudagent.protocols.actionmenu"

MESSAGE_TYPES = {
    MENU: f"{PROTOCOL_PACKAGE}.messages.menu.Menu",
    MENU_REQUEST: (f"{PROTOCOL_PACKAGE}.messages.menu_request.MenuRequest"),
    PERFORM: f"{PROTOCOL_PACKAGE}.messages.perform.Perform",
    NEW_MENU: f"{PROTOCOL_PACKAGE}.messages.menu.Menu",
    NEW_MENU_REQUEST: (f"{PROTOCOL_PACKAGE}.messages.menu_request.MenuRequest"),
    NEW_PERFORM: f"{PROTOCOL_PACKAGE}.messages.perform.Perform",
}

CONTROLLERS = {PROTOCOL_URI: f"{PROTOCOL_PACKAGE}.controller.Controller"}
