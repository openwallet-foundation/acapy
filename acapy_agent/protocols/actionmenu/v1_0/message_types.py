"""Message type identifiers for Action Menus."""

from ...didcomm_prefix import DIDCommPrefix

# Message types
MENU = "action-menu/1.0/menu"
MENU_REQUEST = "action-menu/1.0/menu-request"
PERFORM = "action-menu/1.0/perform"

PROTOCOL_PACKAGE = "aries_cloudagent.protocols.actionmenu.v1_0"

MESSAGE_TYPES = DIDCommPrefix.qualify_all(
    {
        MENU: f"{PROTOCOL_PACKAGE}.messages.menu.Menu",
        MENU_REQUEST: f"{PROTOCOL_PACKAGE}.messages.menu_request.MenuRequest",
        PERFORM: f"{PROTOCOL_PACKAGE}.messages.perform.Perform",
    }
)

CONTROLLERS = DIDCommPrefix.qualify_all(
    {"action-menu/1.0": f"{PROTOCOL_PACKAGE}.controller.Controller"}
)
