"""Module docstring."""

import asyncio
import binascii
import logging
import threading
from typing import Optional, Sequence

from psycopg import errors as psycopg_errors
from psycopg import pq

from ...category_registry import get_release
from ...dbstore import AbstractDatabaseSession, Entry
from ...error import DBStoreError, DBStoreErrorCode
from ..errors import DatabaseError, DatabaseErrorCode
from .database import PostgresDatabase

LOGGER = logging.getLogger(__name__ + ".DBStore")


class PostgresSession(AbstractDatabaseSession):
    """PostgreSQL database session implementation."""

    def __init__(
        self,
        database: PostgresDatabase,
        profile: str,
        is_txn: bool,
        release_number: str = "release_0",
        profile_id: int = None,
    ):
        """Initialize PostgreSQL session.

        Args:
            database: The PostgresDatabase instance
            profile: Profile name
            is_txn: Whether this is a transaction
            release_number: Schema release number
            profile_id: Optional cached profile ID (avoids DB lookup)

        """
        self.lock = threading.RLock()
        self.database = database
        self.pool = database.pool
        self.profile = profile
        self.is_txn = is_txn
        self.release_number = release_number
        self.conn = None
        self.profile_id = profile_id
        self.schema_context = database.schema_context

    def _get_handler(self, category: str):
        """Get a handler for the given category with the correct schema context.

        Handlers are created at module load time with a default schema context.
        This method updates the handler's schema context to match the session's
        schema context before returning it.
        """
        handlers, _, _ = get_release(self.release_number, "postgresql")
        handler = handlers.get(category, handlers["default"])
        # Update handler's schema context to match session's schema context
        if hasattr(handler, "set_schema_context"):
            handler.set_schema_context(self.schema_context)
        return handler

    def _process_value(
        self, value: str | bytes, operation: str, name: str, category: str
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
                        message=(
                            f"Failed to decode bytes value for '{name}' in category "
                            f"'{category}'"
                        ),
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
                        message=(
                            f"Failed to decode hex-encoded value for '{name}' in "
                            f"category '{category}'"
                        ),
                        actual_error=str(e),
                    )
            return value
        raise ValueError(f"Invalid operation: {operation}")

    def translate_error(self, error: Exception) -> DBStoreError:
        """Translate database-specific errors to DBStoreError."""
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
        try:
            async with self.conn.cursor() as cursor:
                await cursor.execute(
                    f"SELECT id FROM {self.schema_context.qualify_table('profiles')} "
                    f"WHERE name = %s",
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

    async def __aenter__(self):
        """Enter async context manager."""
        max_retries = 5
        for attempt in range(max_retries):
            try:
                await self._acquire_and_validate_connection()
                await self._setup_session()
                self._log_session_start()
                return self
            except asyncio.CancelledError:
                await self._cleanup_connection()
                raise
            except Exception as e:
                await self._cleanup_connection()
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue
                self._handle_session_failure(max_retries, e)

    async def _acquire_and_validate_connection(self):
        """Acquire database connection from pool.

        Note: Connection validation is handled by the pool and getconn's rollback.
        The retry logic in __aenter__ handles any stale connection issues.
        """
        self.conn = await self.pool.getconn()

    async def _setup_session(self):
        """Setup session with profile and transaction state."""
        if self.profile_id is None:
            self.profile_id = await self._get_profile_id(self.profile)
        if self.is_txn:
            await self.conn.execute("BEGIN")

    def _log_session_start(self):
        """Log session start information."""
        LOGGER.debug(
            "[enter_session] Starting for profile=%s, is_txn=%s, release_number=%s",
            self.profile,
            self.is_txn,
            self.release_number,
        )

    async def _cleanup_connection(self):
        """Clean up database connection during session setup failure."""
        if self.conn:
            try:
                await self.conn.rollback()
            except Exception as e:
                LOGGER.warning("[cleanup_connection] Rollback failed: %s", str(e))

            try:
                await self.pool.putconn(self.conn)
            except Exception as e:
                LOGGER.error(
                    "[cleanup_connection] CRITICAL: Failed to return connection: %s",
                    str(e),
                )
            finally:
                self.conn = None

    def _handle_session_failure(self, max_retries: int, error: Exception):
        """Handle session setup failure after retries."""
        LOGGER.error(
            "Failed to enter session after %d retries: %s", max_retries, str(error)
        )
        raise DatabaseError(
            code=DatabaseErrorCode.CONNECTION_ERROR,
            message="Failed to enter session",
            actual_error=str(error),
        )

    async def __aexit__(self, exc_type, exc, tb):
        """Exit async context manager."""
        cancelled_during_exit = False
        if self.conn:
            cancelled_during_exit = await self._handle_transaction_completion(exc_type)
            await self._cleanup_session()

        if cancelled_during_exit:
            raise asyncio.CancelledError

    async def _handle_transaction_completion(self, exc_type) -> bool:
        """Handle transaction commit/rollback and return if cancelled."""
        cancelled_during_exit = False
        try:
            if self.is_txn:
                await self._handle_transaction_mode(exc_type)
            else:
                await self._handle_non_transaction_mode()
        except asyncio.CancelledError:
            await self.conn.rollback()
            cancelled_during_exit = True
        except Exception:
            await self.conn.rollback()
        return cancelled_during_exit

    async def _handle_transaction_mode(self, exc_type):
        """Handle transaction completion in transaction mode."""
        if exc_type is None:
            await self.conn.commit()
        else:
            await self.conn.rollback()

    async def _handle_non_transaction_mode(self):
        """Handle transaction completion in non-transaction mode."""
        if self.conn.pgconn.transaction_status != pq.TransactionStatus.IDLE:
            await self.conn.commit()

    async def _cleanup_session(self):
        """Clean up session resources."""
        conn_returned = False
        try:
            await self.pool.putconn(self.conn)
            conn_returned = True
            self.conn = None
        except Exception as e:
            LOGGER.error(
                "[close_session] CRITICAL: Failed to return connection to pool: %s",
                str(e),
            )
            self.conn = None

        try:
            if self in self.database.active_sessions:
                self.database.active_sessions.remove(self)
        except Exception as e:
            LOGGER.warning(
                "[close_session] Failed to remove from active_sessions: %s", str(e)
            )

        LOGGER.debug("[close_session] Completed (connection_returned=%s)", conn_returned)

    async def count(self, category: str, tag_filter: str | dict = None) -> int:
        """Count entries in a category."""
        handler = self._get_handler(category)
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
            except DatabaseError:
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
        value: str | bytes = None,
        tags: dict = None,
        expiry_ms: int = None,
    ):
        """Insert an entry."""
        handler = self._get_handler(category)
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
            except DatabaseError:
                # Re-raise DatabaseError as-is to preserve original error code
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
        tag_filter: str | dict = None,
        for_update: bool = False,
    ) -> Optional[Entry]:
        """Fetch a single entry."""
        handler = self._get_handler(category)
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
            except DatabaseError:
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
        tag_filter: str | dict = None,
        limit: int = None,
        for_update: bool = False,
        order_by: Optional[str] = None,
        descending: bool = False,
    ) -> Sequence[Entry]:
        """Fetch all entries matching criteria."""
        handler = self._get_handler(category)
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
            except DatabaseError:
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
        value: str | bytes = None,
        tags: dict = None,
        expiry_ms: int = None,
    ):
        """Replace an entry."""
        handler = self._get_handler(category)
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
            except DatabaseError:
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
        """Remove a single entry."""
        handler = self._get_handler(category)
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
            except DatabaseError:
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

    async def remove_all(self, category: str, tag_filter: str | dict = None) -> int:
        """Remove all entries matching criteria."""
        handler = self._get_handler(category)
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
            except DatabaseError:
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
        """Commit transaction."""
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
        """Rollback transaction."""
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
        """Close session."""
        if self.conn:
            try:
                await self.pool.putconn(self.conn)
            except Exception as e:
                LOGGER.error("[close] CRITICAL: Failed to return connection: %s", str(e))
            finally:
                self.conn = None

            try:
                if self in self.database.active_sessions:
                    self.database.active_sessions.remove(self)
            except Exception as e:
                LOGGER.warning(
                    "[close] Failed to remove from active_sessions: %s", str(e)
                )

            LOGGER.debug("[close] Completed")
