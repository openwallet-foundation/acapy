import threading
import asyncio
from typing import Optional, Union, Sequence
import binascii

from psycopg import pq, errors as psycopg_errors
from ...dbstore import AbstractDatabaseSession, Entry
from ...error import DBStoreError, DBStoreErrorCode
from .database import PostgresDatabase
from ..errors import DatabaseError, DatabaseErrorCode
from ...category_registry import get_release
import logging

LOGGER = logging.getLogger(__name__ + ".DBStore")


class PostgresSession(AbstractDatabaseSession):
    def __init__(
        self,
        database: PostgresDatabase,
        profile: str,
        is_txn: bool,
        release_number: str = "release_1",
    ):
        self.lock = threading.RLock()
        self.database = database
        self.pool = database.pool
        self.profile = profile
        self.is_txn = is_txn
        self.release_number = release_number
        self.conn = None
        self.profile_id = None
        self.schema_context = database.schema_context

    def _process_value(
        self, value: Union[str, bytes], operation: str, name: str, category: str
    ) -> str:
        """Process items.value for insert/replace (encode) or fetch/fetch_all (decode)."""
        if operation in ("insert", "replace"):
            if isinstance(value, bytes):
                try:
                    processed_value = value.decode("utf-8")
                    LOGGER.debug(
                        "Converted bytes to UTF-8 string for %s in category %s: %s",
                        name,
                        category,
                        processed_value,
                    )
                    return processed_value
                except UnicodeDecodeError as e:
                    LOGGER.error(
                        "Failed to decode bytes value for %s in category %s: %s",
                        name,
                        category,
                        str(e),
                    )
                    raise DatabaseError(
                        code=DatabaseErrorCode.QUERY_ERROR,
                        message=f"Failed to decode bytes value for '{name}' in category '{category}'",
                        actual_error=str(e),
                    )
            return value or ""
        elif operation in ("fetch", "fetch_all"):
            if isinstance(value, str) and value.startswith("\\x"):
                try:
                    decoded_bytes = binascii.unhexlify(value.replace("\\x", ""))
                    processed_value = decoded_bytes.decode("utf-8")
                    LOGGER.debug(
                        "Decoded hex value for %s in category %s: %s",
                        name,
                        category,
                        processed_value,
                    )
                    return processed_value
                except (binascii.Error, UnicodeDecodeError) as e:
                    LOGGER.error(
                        "Failed to decode hex-encoded value for %s in category %s: %s",
                        name,
                        category,
                        str(e),
                    )
                    raise DatabaseError(
                        code=DatabaseErrorCode.QUERY_ERROR,
                        message=f"Failed to decode hex-encoded value for '{name}' in category '{category}'",
                        actual_error=str(e),
                    )
            return value
        raise ValueError(f"Invalid operation: {operation}")

    def translate_error(self, error: Exception) -> DBStoreError:
        if self.database.backend:
            return self.database.backend.translate_error(error)
        LOGGER.debug("Translating error: %s, type=%s", str(error), type(error))
        if isinstance(error, DatabaseError):
            return DBStoreError(
                code=DBStoreErrorCode.UNEXPECTED, message=f"Database error: {str(error)}"
            )
        elif isinstance(error, psycopg_errors.UniqueViolation):
            return DBStoreError(
                code=DBStoreErrorCode.DUPLICATE, message=f"Duplicate entry: {str(error)}"
            )
        elif isinstance(error, psycopg_errors.OperationalError):
            return DBStoreError(
                code=DBStoreErrorCode.BACKEND,
                message=f"Database operation failed: {str(error)}",
            )
        elif isinstance(error, ValueError):
            return DBStoreError(
                code=DBStoreErrorCode.UNEXPECTED,
                message=f"Configuration error: {str(error)}",
            )
        return DBStoreError(
            code=DBStoreErrorCode.UNEXPECTED, message=f"Unexpected error: {str(error)}"
        )

    async def _get_profile_id(self, profile_name: str) -> int:
        conn = await self.pool.getconn()
        try:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"SELECT id FROM {self.schema_context.qualify_table('profiles')} WHERE name = %s",
                    (profile_name,),
                )
                row = await cursor.fetchone()
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
            await conn.rollback()
            await self.pool.putconn(conn)

    async def __aenter__(self):
        max_retries = 5
        for attempt in range(max_retries):
            try:
                self.conn = await self.pool.getconn(timeout=60.0)
                try:
                    async with self.conn.cursor() as cursor:
                        await cursor.execute("SELECT 1")
                except Exception as e:
                    await self.conn.rollback()
                    await self.pool.putconn(self.conn)
                    self.conn = None
                    LOGGER.error("Invalid connection retrieved: %s", str(e))
                    raise DatabaseError(
                        code=DatabaseErrorCode.CONNECTION_ERROR,
                        message="Invalid connection retrieved from pool",
                        actual_error=str(e),
                    )
                if self.profile_id is None:
                    self.profile_id = await self._get_profile_id(self.profile)
                if self.is_txn:
                    await self.conn.execute("BEGIN")
                LOGGER.debug(
                    "[enter_session] Starting for profile=%s, is_txn=%s, release_number=%s",
                    self.profile,
                    self.is_txn,
                    self.release_number,
                )
                return self
            except asyncio.CancelledError:
                if self.conn:
                    await self.conn.rollback()
                    await self.pool.putconn(self.conn)
                    self.conn = None
                raise
            except Exception as e:
                if self.conn:
                    await self.conn.rollback()
                    await self.pool.putconn(self.conn)
                    self.conn = None
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
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
                        await self.conn.commit()
                    else:
                        await self.conn.rollback()
                else:
                    if self.conn.pgconn.transaction_status != pq.TransactionStatus.IDLE:
                        await self.conn.commit()
            except asyncio.CancelledError:
                await self.conn.rollback()
            except Exception:
                await self.conn.rollback()
            finally:
                try:
                    await self.conn.rollback()
                    await self.pool.putconn(self.conn)
                    self.conn = None
                    if self in self.database.active_sessions:
                        self.database.active_sessions.remove(self)
                    LOGGER.debug("[close_session] Completed")
                except Exception:
                    pass

    async def count(self, category: str, tag_filter: Union[str, dict] = None) -> int:
        handlers, _, _ = get_release(self.release_number, "postgresql")
        handler = handlers.get(category, handlers["default"])
        async with self.conn.cursor() as cursor:
            try:
                count = await handler.count(cursor, self.profile_id, category, tag_filter)
                if (
                    not self.is_txn
                    and self.conn.pgconn.transaction_status != pq.TransactionStatus.IDLE
                ):
                    await self.conn.commit()
                return count
            except asyncio.CancelledError:
                if not self.is_txn:
                    await self.conn.rollback()
                raise
            except Exception as e:
                if not self.is_txn:
                    await self.conn.rollback()
                LOGGER.error(
                    "Failed to count items in category '%s': %s", category, str(e)
                )
                raise DatabaseError(
                    code=DatabaseErrorCode.QUERY_ERROR,
                    message=f"Failed to count items in category '{category}'",
                    actual_error=str(e),
                )

    async def insert(
        self,
        category: str,
        name: str,
        value: Union[str, bytes] = None,
        tags: dict = None,
        expiry_ms: int = None,
    ):
        handlers, _, _ = get_release(self.release_number, "postgresql")
        handler = handlers.get(category, handlers["default"])
        value = self._process_value(value, "insert", name, category)
        async with self.conn.cursor() as cursor:
            try:
                await handler.insert(
                    cursor, self.profile_id, category, name, value, tags or {}, expiry_ms
                )
                if (
                    not self.is_txn
                    and self.conn.pgconn.transaction_status != pq.TransactionStatus.IDLE
                ):
                    await self.conn.commit()
            except asyncio.CancelledError:
                if not self.is_txn:
                    await self.conn.rollback()
                raise
            except Exception as e:
                if not self.is_txn:
                    await self.conn.rollback()
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

    async def fetch(
        self,
        category: str,
        name: str,
        tag_filter: Union[str, dict] = None,
        for_update: bool = False,
    ) -> Optional[Entry]:
        handlers, _, _ = get_release(self.release_number, "postgresql")
        handler = handlers.get(category, handlers["default"])
        async with self.conn.cursor() as cursor:
            try:
                result = await handler.fetch(
                    cursor, self.profile_id, category, name, tag_filter, for_update
                )
                if result:
                    result = Entry(
                        category=result.category,
                        name=result.name,
                        value=self._process_value(result.value, "fetch", name, category),
                        tags=result.tags,
                    )
                if (
                    not self.is_txn
                    and self.conn.pgconn.transaction_status != pq.TransactionStatus.IDLE
                ):
                    await self.conn.commit()
                return result
            except asyncio.CancelledError:
                if not self.is_txn:
                    await self.conn.rollback()
                raise
            except Exception as e:
                if not self.is_txn:
                    await self.conn.rollback()
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

    async def fetch_all(
        self,
        category: str,
        tag_filter: Union[str, dict] = None,
        limit: int = None,
        for_update: bool = False,
        order_by: Optional[str] = None,
        descending: bool = False,
    ) -> Sequence[Entry]:
        handlers, _, _ = get_release(self.release_number, "postgresql")
        handler = handlers.get(category, handlers["default"])
        async with self.conn.cursor() as cursor:
            try:
                results = await handler.fetch_all(
                    cursor,
                    self.profile_id,
                    category,
                    tag_filter,
                    limit,
                    for_update,
                    order_by,
                    descending,
                )
                decoded_results = [
                    Entry(
                        category=result.category,
                        name=result.name,
                        value=self._process_value(
                            result.value, "fetch_all", result.name, category
                        ),
                        tags=result.tags,
                    )
                    for result in results
                ]
                if (
                    not self.is_txn
                    and self.conn.pgconn.transaction_status != pq.TransactionStatus.IDLE
                ):
                    await self.conn.commit()
                return decoded_results
            except asyncio.CancelledError:
                if not self.is_txn:
                    await self.conn.rollback()
                raise
            except Exception as e:
                if not self.is_txn:
                    await self.conn.rollback()
                LOGGER.error(
                    "Failed to fetch all items in category '%s': %s", category, str(e)
                )
                raise DatabaseError(
                    code=DatabaseErrorCode.QUERY_ERROR,
                    message=f"Failed to fetch all items in category '{category}'",
                    actual_error=str(e),
                )

    async def replace(
        self,
        category: str,
        name: str,
        value: Union[str, bytes] = None,
        tags: dict = None,
        expiry_ms: int = None,
    ):
        handlers, _, _ = get_release(self.release_number, "postgresql")
        handler = handlers.get(category, handlers["default"])
        value = self._process_value(value, "replace", name, category)
        async with self.conn.cursor() as cursor:
            try:
                await handler.replace(
                    cursor, self.profile_id, category, name, value, tags or {}, expiry_ms
                )
                if (
                    not self.is_txn
                    and self.conn.pgconn.transaction_status != pq.TransactionStatus.IDLE
                ):
                    await self.conn.commit()
            except asyncio.CancelledError:
                if not self.is_txn:
                    await self.conn.rollback()
                raise
            except Exception as e:
                if not self.is_txn:
                    await self.conn.rollback()
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

    async def remove(self, category: str, name: str):
        handlers, _, _ = get_release(self.release_number, "postgresql")
        handler = handlers.get(category, handlers["default"])
        async with self.conn.cursor() as cursor:
            try:
                await handler.remove(cursor, self.profile_id, category, name)
                if (
                    not self.is_txn
                    and self.conn.pgconn.transaction_status != pq.TransactionStatus.IDLE
                ):
                    await self.conn.commit()
            except asyncio.CancelledError:
                if not self.is_txn:
                    await self.conn.rollback()
                raise
            except Exception as e:
                if not self.is_txn:
                    await self.conn.rollback()
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

    async def remove_all(self, category: str, tag_filter: Union[str, dict] = None) -> int:
        handlers, _, _ = get_release(self.release_number, "postgresql")
        handler = handlers.get(category, handlers["default"])
        async with self.conn.cursor() as cursor:
            try:
                result = await handler.remove_all(
                    cursor, self.profile_id, category, tag_filter
                )
                if (
                    not self.is_txn
                    and self.conn.pgconn.transaction_status != pq.TransactionStatus.IDLE
                ):
                    await self.conn.commit()
                return result
            except asyncio.CancelledError:
                if not self.is_txn:
                    await self.conn.rollback()
                raise
            except Exception as e:
                if not self.is_txn:
                    await self.conn.rollback()
                LOGGER.error(
                    "Failed to remove all items in category '%s': %s", category, str(e)
                )
                raise DatabaseError(
                    code=DatabaseErrorCode.QUERY_ERROR,
                    message=f"Failed to remove all items in category '{category}'",
                    actual_error=str(e),
                )

    async def commit(self):
        if not self.is_txn:
            raise DBStoreError(DBStoreErrorCode.WRAPPER, "Not a transaction")
        try:
            await self.conn.commit()
        except asyncio.CancelledError:
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
            await self.conn.rollback()
        except asyncio.CancelledError:
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
                async with self.conn.cursor() as cursor:
                    await cursor.execute("SELECT 1")
            except Exception:
                pass
            try:
                await self.conn.rollback()
                await self.pool.putconn(self.conn)
                self.conn = None
                if self in self.database.active_sessions:
                    self.database.active_sessions.remove(self)
                LOGGER.debug("[close_session] Completed")
            except Exception:
                pass
