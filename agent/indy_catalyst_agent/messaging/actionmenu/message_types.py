"""Message type identifiers for Action Menus."""

MESSAGE_FAMILY = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/action-menu/1.0"

MENU = f"{MESSAGE_FAMILY}/menu"
MENU_REQUEST = f"{MESSAGE_FAMILY}/menu-request"
PERFORM = f"{MESSAGE_FAMILY}/perform"

MESSAGE_TYPES = {
    MENU: "indy_catalyst_agent.messaging.actionmenu.messages.menu.Menu",
    MENU_REQUEST: (
        "indy_catalyst_agent.messaging.actionmenu.messages.menu_request.MenuRequest"
    ),
    PERFORM: "indy_catalyst_agent.messaging.actionmenu.messages.perform.Perform",
}

CONTROLLERS = {
    MESSAGE_FAMILY: "indy_catalyst_agent.messaging.actionmenu.controller.Controller"
}
