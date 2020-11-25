"""Action menu utility methods."""

from ....config.injection_context import InjectionContext
from ....messaging.responder import BaseResponder
from ....storage.base import (
    BaseStorage,
    StorageRecord,
    StorageNotFoundError,
)

from .messages.menu import Menu

MENU_RECORD_TYPE = "connection-action-menu"


async def retrieve_connection_menu(
    connection_id: str, context: InjectionContext
) -> Menu:
    """Retrieve the previously-received action menu."""
    storage: BaseStorage = context.inject(BaseStorage)
    try:
        record = await storage.find_record(
            MENU_RECORD_TYPE, {"connection_id": connection_id}
        )
    except StorageNotFoundError:
        record = None
    return Menu.from_json(record.value) if record else None


async def save_connection_menu(
    menu: Menu, connection_id: str, context: InjectionContext
):
    """Save a received action menu."""

    storage: BaseStorage = context.inject(BaseStorage)
    try:
        record = await storage.find_record(
            MENU_RECORD_TYPE, {"connection_id": connection_id}
        )
    except StorageNotFoundError:
        if menu:
            record = StorageRecord(
                type=MENU_RECORD_TYPE,
                value=menu.to_json(),
                tags={"connection_id": connection_id},
            )
            await storage.add_record(record)
    else:
        if menu:
            await storage.update_record(
                record, menu.to_json(), {"connection_id": connection_id}
            )
        else:
            await storage.delete_record(record)

    responder: BaseResponder = context.inject(BaseResponder, required=False)
    if responder:
        await responder.send_webhook(
            "actionmenu",
            {
                "connection_id": connection_id,
                "menu": menu.serialize() if menu else None,
            },
        )
