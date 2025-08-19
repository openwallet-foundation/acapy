import threading
import asyncio
from typing import Optional, Union, Sequence

from ...dbstore import AbstractDatabaseSession, Entry
from ...error import DBStoreError, DBStoreErrorCode
from .database import SqliteDatabase
from ..errors import DatabaseError, DatabaseErrorCode
from ...category_registry import get_release
import logging

LOGGER = logging.getLogger(__name__ + ".DBStore")


class SqliteSession(AbstractDatabaseSession):
    def __init__(
        self,
        database: SqliteDatabase,
        profile: str,
        is_txn: bool,
        release_number: str = "release_0_1",
    ):
        self.lock = threading.RLock()
        self.database = database
        self.pool = database.pool
        self.profile = profile
        self.is_txn = is_txn
        self.release_number = release_number
        self.conn = None
        self.profile_id = None

    def _get_profile_id(self, profile_name: str) -> int:
        with self.lock:
            conn = self.pool.get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM profiles WHERE name = ?", (profile_name,))
                row = cursor.fetchone()
                if row:
                    return row[0]
                LOGGER.error("Profile '%s' not found", profile_name)
                raise DatabaseError(
                    code=DatabaseErrorCode.PROFILE_NOT_FOUND,
                    message=f"Profile '{profile_name}' not found",
                )
            except Exception as e:
                LOGGER.error(
                    "Failed to retrieve profile ID for '%s': %s", profile_name, str(e)
                )
                raise DatabaseError(
                    code=DatabaseErrorCode.QUERY_ERROR,
                    message=f"Failed to retrieve profile ID for '{profile_name}'",
                    actual_error=str(e),
                )
            finally:
                self.pool.return_connection(conn)

    async def __aenter__(self):
        max_retries = 5
        for attempt in range(max_retries):
            try:
                # Limits the time spent waiting to acquire a connection from the pool during session initialization.
                self.conn = await asyncio.to_thread(
                    self.pool.get_connection, timeout=60.0
                )
                try:
                    cursor = await asyncio.to_thread(self.conn.cursor)
                    await asyncio.to_thread(cursor.execute, "SELECT 1")
                    if (
                        not hasattr(self.pool, "encryption_key")
                        or not self.pool.encryption_key
                    ):
                        await asyncio.to_thread(cursor.execute, "BEGIN")
                        await asyncio.to_thread(cursor.execute, "ROLLBACK")
                except Exception as e:
                    await asyncio.to_thread(self.pool.return_connection, self.conn)
                    self.conn = None
                    LOGGER.error("Invalid connection retrieved: %s", str(e))
                    raise DatabaseError(
                        code=DatabaseErrorCode.CONNECTION_ERROR,
                        message="Invalid connection retrieved from pool",
                        actual_error=str(e),
                    )
                if self.profile_id is None:
                    self.profile_id = await asyncio.to_thread(
                        self._get_profile_id, self.profile
                    )
                if self.is_txn:
                    await asyncio.to_thread(self.conn.execute, "BEGIN")
                LOGGER.debug(
                    "[enter_session] Starting for profile=%s, is_txn=%s, release_number=%s",
                    self.profile,
                    self.is_txn,
                    self.release_number,
                )
                return self
            except asyncio.exceptions.CancelledError:
                if self.conn:
                    await asyncio.to_thread(self.pool.return_connection, self.conn)
                    self.conn = None
                raise
            except Exception as e:
                if self.conn:
                    await asyncio.to_thread(self.pool.return_connection, self.conn)
                    self.conn = None
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)  # Wait before retry
                    continue
                LOGGER.error(
                    "Failed to enter session after %d retries: %s", max_retries, str(e)
                )
                raise DatabaseError(
                    code=DatabaseErrorCode.CONNECTION_ERROR,
                    message="Failed to enter session",
                    actual_error=str(e),
                )

    async def __aexit__(self, exc_type, exc, tb):
        if self.conn:
            try:
                if self.is_txn:
                    if exc_type is None:
                        await asyncio.to_thread(self.conn.commit)
                    else:
                        await asyncio.to_thread(self.conn.rollback)
            except asyncio.exceptions.CancelledError:
                await asyncio.to_thread(self.conn.rollback)
            except Exception:
                pass
            finally:
                try:
                    await asyncio.to_thread(self.pool.return_connection, self.conn)
                    self.conn = None
                    if self in self.database.active_sessions:
                        self.database.active_sessions.remove(self)
                    LOGGER.debug("[close_session] Completed")
                except Exception:
                    pass

    async def count(self, category: str, tag_filter: Union[str, dict] = None) -> int:
        handlers, _, _ = get_release(self.release_number, "sqlite")

        handler = handlers.get(category, handlers["default"])

        def _count():
            with self.lock:
                try:
                    cursor = self.conn.cursor()
                    return handler.count(cursor, self.profile_id, category, tag_filter)
                except asyncio.exceptions.CancelledError:
                    raise
                except Exception as e:
                    LOGGER.error(
                        "Failed to count items in category '%s': %s", category, str(e)
                    )
                    raise DatabaseError(
                        code=DatabaseErrorCode.QUERY_ERROR,
                        message=f"Failed to count items in category '{category}'",
                        actual_error=str(e),
                    )

        return await asyncio.to_thread(_count)

    async def insert(
        self,
        category: str,
        name: str,
        value: Union[str, bytes] = None,
        tags: dict = None,
        expiry_ms: int = None,
    ):
        handlers, _, _ = get_release(self.release_number, "sqlite")
        handler = handlers.get(category, handlers["default"])

        def _insert():
            with self.lock:
                try:
                    cursor = self.conn.cursor()
                    handler.insert(
                        cursor,
                        self.profile_id,
                        category,
                        name,
                        value,
                        tags or {},
                        expiry_ms,
                    )
                    if not self.is_txn:
                        self.conn.commit()
                except asyncio.exceptions.CancelledError:
                    if not self.is_txn:
                        self.conn.rollback()
                    raise
                except Exception as e:
                    if not self.is_txn:
                        self.conn.rollback()
                    LOGGER.error(
                        "Failed to insert item '%s' in category '%s': %s",
                        name,
                        category,
                        str(e),
                    )
                    raise DatabaseError(
                        code=DatabaseErrorCode.QUERY_ERROR,
                        message=f"Failed to insert item '{name}' in category '{category}'",
                        actual_error=str(e),
                    )

        await asyncio.to_thread(_insert)

    async def fetch(
        self,
        category: str,
        name: str,
        tag_filter: Union[str, dict] = None,
        for_update: bool = False,
    ) -> Optional[Entry]:
        handlers, _, _ = get_release(self.release_number, "sqlite")
        handler = handlers.get(category, handlers["default"])

        def _fetch():
            with self.lock:
                try:
                    cursor = self.conn.cursor()
                    return handler.fetch(
                        cursor, self.profile_id, category, name, tag_filter, for_update
                    )
                except asyncio.exceptions.CancelledError:
                    raise
                except Exception as e:
                    LOGGER.error(
                        "Failed to fetch item '%s' in category '%s': %s",
                        name,
                        category,
                        str(e),
                    )
                    raise DatabaseError(
                        code=DatabaseErrorCode.QUERY_ERROR,
                        message=f"Failed to fetch item '{name}' in category '{category}'",
                        actual_error=str(e),
                    )

        return await asyncio.to_thread(_fetch)

    async def fetch_all(
        self,
        category: str,
        tag_filter: Union[str, dict] = None,
        limit: int = None,
        for_update: bool = False,
        order_by: Optional[str] = None,
        descending: bool = False,
    ) -> Sequence[Entry]:
        handlers, _, _ = get_release(self.release_number, "sqlite")
        handler = handlers.get(category, handlers["default"])

        def _fetch_all():
            with self.lock:
                try:
                    cursor = self.conn.cursor()
                    return handler.fetch_all(
                        cursor,
                        self.profile_id,
                        category,
                        tag_filter,
                        limit,
                        for_update,
                        order_by,
                        descending,
                    )
                except asyncio.exceptions.CancelledError:
                    raise
                except Exception as e:
                    LOGGER.error(
                        "Failed to fetch all items in category '%s': %s", category, str(e)
                    )
                    raise DatabaseError(
                        code=DatabaseErrorCode.QUERY_ERROR,
                        message=f"Failed to fetch all items in category '{category}'",
                        actual_error=str(e),
                    )

        return await asyncio.to_thread(_fetch_all)

    async def replace(
        self,
        category: str,
        name: str,
        value: Union[str, bytes] = None,
        tags: dict = None,
        expiry_ms: int = None,
    ):
        handlers, _, _ = get_release(self.release_number, "sqlite")
        handler = handlers.get(category, handlers["default"])

        def _replace():
            with self.lock:
                try:
                    cursor = self.conn.cursor()
                    handler.replace(
                        cursor,
                        self.profile_id,
                        category,
                        name,
                        value,
                        tags or {},
                        expiry_ms,
                    )
                    if not self.is_txn:
                        self.conn.commit()
                except asyncio.exceptions.CancelledError:
                    if not self.is_txn:
                        self.conn.rollback()
                    raise
                except Exception as e:
                    if not self.is_txn:
                        self.conn.rollback()
                    LOGGER.error(
                        "Failed to replace item '%s' in category '%s': %s",
                        name,
                        category,
                        str(e),
                    )
                    raise DatabaseError(
                        code=DatabaseErrorCode.QUERY_ERROR,
                        message=f"Failed to replace item '{name}' in category '{category}'",
                        actual_error=str(e),
                    )

        await asyncio.to_thread(_replace)

    async def remove(self, category: str, name: str):
        handlers, _, _ = get_release(self.release_number, "sqlite")
        handler = handlers.get(category, handlers["default"])

        def _remove():
            with self.lock:
                try:
                    cursor = self.conn.cursor()
                    handler.remove(cursor, self.profile_id, category, name)
                    if not self.is_txn:
                        self.conn.commit()
                except asyncio.exceptions.CancelledError:
                    if not self.is_txn:
                        self.conn.rollback()
                    raise
                except Exception as e:
                    if not self.is_txn:
                        self.conn.rollback()
                    LOGGER.error(
                        "Failed to remove item '%s' in category '%s': %s",
                        name,
                        category,
                        str(e),
                    )
                    raise DatabaseError(
                        code=DatabaseErrorCode.QUERY_ERROR,
                        message=f"Failed to remove item '{name}' in category '{category}'",
                        actual_error=str(e),
                    )

        await asyncio.to_thread(_remove)

    async def remove_all(self, category: str, tag_filter: Union[str, dict] = None) -> int:
        handlers, _, _ = get_release(self.release_number, "sqlite")
        handler = handlers.get(category, handlers["default"])

        def _remove_all():
            with self.lock:
                try:
                    cursor = self.conn.cursor()
                    result = handler.remove_all(
                        cursor, self.profile_id, category, tag_filter
                    )
                    if not self.is_txn:
                        self.conn.commit()
                    return result
                except asyncio.exceptions.CancelledError:
                    if not self.is_txn:
                        self.conn.rollback()
                    raise
                except Exception as e:
                    if not self.is_txn:
                        self.conn.rollback()
                    LOGGER.error(
                        "Failed to remove all items in category '%s': %s",
                        category,
                        str(e),
                    )
                    raise DatabaseError(
                        code=DatabaseErrorCode.QUERY_ERROR,
                        message=f"Failed to remove all items in category '{category}'",
                        actual_error=str(e),
                    )

        return await asyncio.to_thread(_remove_all)

    async def commit(self):
        if not self.is_txn:
            raise DBStoreError(DBStoreErrorCode.WRAPPER, "Not a transaction")
        try:
            await asyncio.to_thread(self.conn.commit)
        except asyncio.exceptions.CancelledError:
            raise
        except Exception as e:
            LOGGER.error("Failed to commit transaction: %s", str(e))
            raise DatabaseError(
                code=DatabaseErrorCode.QUERY_ERROR,
                message="Failed to commit transaction",
                actual_error=str(e),
            )

    async def rollback(self):
        if not self.is_txn:
            raise DBStoreError(DBStoreErrorCode.WRAPPER, "Not a transaction")
        try:
            await asyncio.to_thread(self.conn.rollback)
        except asyncio.exceptions.CancelledError:
            raise
        except Exception as e:
            LOGGER.error("Failed to rollback transaction: %s", str(e))
            raise DatabaseError(
                code=DatabaseErrorCode.QUERY_ERROR,
                message="Failed to rollback transaction",
                actual_error=str(e),
            )

    async def close(self):
        if self.conn:
            try:
                cursor = await asyncio.to_thread(self.conn.cursor)
                cursor.execute("SELECT 1")
            except Exception:
                pass
            try:
                await asyncio.to_thread(self.pool.return_connection, self.conn)
                self.conn = None
                if self in self.database.active_sessions:
                    self.database.active_sessions.remove(self)
                LOGGER.debug("[close_session] Completed")
            except Exception:
                pass
