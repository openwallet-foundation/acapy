"""Tests for SQLite minimal database functionality."""

# poetry run python \
# acapy_agent/database_manager/databases/sqlite_normalized/test/\
# test_sqlite_minimal.py

import asyncio
import logging

from acapy_agent.database_manager.databases.sqlite_normalized.config import SqliteConfig
from acapy_agent.database_manager.databases.sqlite_normalized.database import (
    SqliteDatabase,
)

logging.basicConfig(level=logging.DEBUG)
LOGGER = logging.getLogger(__name__)


async def minimal_test():
    """Test minimal SQLite database functionality."""
    store = None
    try:
        config = SqliteConfig(
            uri="sqlite://test.db",
            encryption_key="strong_key",
            pool_size=5,
            schema_config="generic",
        )
        pool, profile_name, path, effective_release_number = config.provision(
            profile="test_profile", recreate=True, release_number="release_0"
        )
        store = SqliteDatabase(pool, profile_name, path, effective_release_number)
        LOGGER.debug(f"Store initialized: {store}, type={type(store)}, id={id(store)}")
        async with store.session() as session:
            await session.insert(category="test", name="test1", value="{'data': 'test'}")
        LOGGER.debug(f"Store before rekey: {store}, type={type(store)}, id={id(store)}")
        await store.rekey(pass_key="new_secure_key")
        LOGGER.debug(f"Store after rekey: {store}, type={type(store)}, id={id(store)}")
        config_new = SqliteConfig(
            uri="sqlite://test.db",
            encryption_key="new_secure_key",
            pool_size=5,
            schema_config="generic",
        )
        pool, profile_name, path, effective_release_number = config_new.provision(
            profile="test_profile", recreate=False, release_number="release_0"
        )
        store = SqliteDatabase(pool, profile_name, path, effective_release_number)
        LOGGER.debug(f"Store after reopen: {store}, type={type(store)}, id={id(store)}")
        async with store.session() as session:
            count = await session.count(category="test")
            LOGGER.debug(f"Counted {count} items")
        LOGGER.debug(f"Store before close: {store}, type={type(store)}, id={id(store)}")
        LOGGER.debug("Test completed successfully")
    except Exception as e:
        LOGGER.error(f"Error in minimal_test: {str(e)}")
        raise
    finally:
        if store is not None:
            LOGGER.debug(
                f"Closing store in finally: {store}, type={type(store)}, id={id(store)}"
            )
            try:
                loop = asyncio.get_event_loop()
                LOGGER.debug(
                    f"Event loop state: running={loop.is_running()}, "
                    f"closed={loop.is_closed()}"
                )
                if hasattr(store, "close") and callable(store.close):
                    LOGGER.debug("Calling store.close")
                    store.close()  # Call synchronously
                    LOGGER.debug("Database closed in finally block")
                else:
                    LOGGER.error("Store.close is not callable or missing")
            except Exception as close_err:
                LOGGER.error(
                    f"Error closing store: {str(close_err)}, "
                    f"store={store}, type={type(store)}"
                )
        else:
            LOGGER.warning("Store is None, skipping close operation.")


if __name__ == "__main__":
    asyncio.run(minimal_test(), debug=True)
