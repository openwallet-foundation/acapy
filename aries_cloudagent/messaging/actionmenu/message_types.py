"""Message type identifiers for Action Menus."""

MESSAGE_FAMILY = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/action-menu/1.0"

MENU = f"{MESSAGE_FAMILY}/menu"
MENU_REQUEST = f"{MESSAGE_FAMILY}/menu-request"
PERFORM = f"{MESSAGE_FAMILY}/perform"

MESSAGE_TYPES = {
    MENU: "aries_cloudagent.messaging.actionmenu.messages.menu.Menu",
    MENU_REQUEST: (
        "aries_cloudagent.messaging.actionmenu.messages.menu_request.MenuRequest"
    ),
    PERFORM: "aries_cloudagent.messaging.actionmenu.messages.perform.Perform",
}

CONTROLLERS = {
    MESSAGE_FAMILY: "aries_cloudagent.messaging.actionmenu.controller.Controller"
}
