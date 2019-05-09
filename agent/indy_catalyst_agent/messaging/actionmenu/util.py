"""Action menu utility methods."""

from ...admin.service import AdminService
from ...config.injection_context import InjectionContext
from .messages.menu import Menu
from ...storage.base import BaseStorage, StorageRecord, StorageNotFoundError

MENU_RECORD_TYPE = "connection-action-menu"


async def retrieve_connection_menu(
    connection_id: str, context: InjectionContext
) -> Menu:
    """Retrieve the previously-received action menu."""
    storage: BaseStorage = await context.inject(BaseStorage)
    try:
        record = await storage.search_records(
            MENU_RECORD_TYPE, {"connection_id": connection_id}
        ).fetch_single()
    except StorageNotFoundError:
        record = None
    return Menu.from_json(record.value) if record else None


async def save_connection_menu(
    menu: Menu, connection_id: str, context: InjectionContext
):
    """Save a received action menu."""

    storage: BaseStorage = await context.inject(BaseStorage)
    try:
        record = await storage.search_records(
            MENU_RECORD_TYPE, {"connection_id": connection_id}
        ).fetch_single()
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
            await storage.update_record_value(record, menu.to_json())
        else:
            await storage.delete_record(record)

    service: AdminService = await context.inject(AdminService, required=False)
    if service:
        await service.add_event(
            "connection_menu",
            {
                "connection_id": connection_id,
                "menu": menu.serialize() if menu else None,
            },
        )
