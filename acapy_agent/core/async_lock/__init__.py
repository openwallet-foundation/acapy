"""Setup for async lock service."""

import json

from ...__main__ import LOGGER
from ...config.injection_context import InjectionContext
from ...utils.base_storage import get_postgres_connection_uri
from .async_lock import AsyncLock
from .async_lock_postgres import PostgresAsyncLock
from .async_lock_sqlite import SqliteAsyncLock


async def setup(context: InjectionContext):
    """Set up the async lock service."""

    storage_type = context.settings.get("wallet.storage_type")

    match storage_type:
        case "postgres_storage":
            LOGGER.info("Setting up and binding PostgresAsyncLock...")
            connection_uri = get_postgres_connection_uri(
                json.loads(context.settings["wallet.storage_creds"]),
                json.loads(context.settings["wallet.storage_config"]),
            )
            await PostgresAsyncLock.create(connection_uri)
            context.injector.bind_instance(AsyncLock, PostgresAsyncLock())

        case "default" | None:
            LOGGER.info("Setting up and binding SqliteAsyncLock...")
            SqliteAsyncLock.create()
            context.injector.bind_instance(AsyncLock, SqliteAsyncLock())

        case _:
            raise ValueError(f"Unsupported storage type for async lock: {storage_type}")
