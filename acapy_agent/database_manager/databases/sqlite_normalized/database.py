"""SQLite normalized database implementation."""

import asyncio
import logging
import sqlite3
import threading
import time
from typing import Generator, Optional

try:
    # Try new sqlcipher3 first (SQLite 3.46+)
    import sqlcipher3 as sqlcipher
except ImportError:
    sqlcipher = None
from ...category_registry import get_release
from ...db_types import Entry
from ...interfaces import AbstractDatabaseStore
from ...wql_normalized.query import query_from_str
from ...wql_normalized.tags import query_to_tagquery
from ..errors import DatabaseError, DatabaseErrorCode
from .connection_pool import ConnectionPool

LOGGER = logging.getLogger(__name__)


def enc_name(name: str) -> str:
    """Encode name for database storage.

    Args:
        name: Name to encode

    Returns:
        Encoded name

    """
    return name


def enc_value(value: str) -> str:
    """Encode value for database storage.

    Args:
        value: Value to encode

    Returns:
        Encoded value

    """
    return value


class SqliteDatabase(AbstractDatabaseStore):
    """SQLite database implementation for normalized storage."""

    def __init__(
        self,
        pool: ConnectionPool,
        default_profile: str,
        path: str,
        release_number: str = "release_0",
    ):
        """Initialize SQLite database."""
        self.lock = threading.RLock()
        self.pool = pool
        self.default_profile = default_profile
        self.path = path
        self.release_number = release_number  # The self.release_number comes
        # from the schema_release_number stored in the config table
        self.active_sessions = []
        self.session_creation_times = {}
        self.max_sessions = int(pool.pool_size * 0.75)  # need load test
        self._monitoring_task: Optional[asyncio.Task] = None

        try:
            self.default_profile_id = self._get_profile_id(default_profile)
        except Exception as e:
            LOGGER.error(
                "Failed to initialize default profile ID for '%s': %s",
                default_profile,
                str(e),
            )
            raise DatabaseError(
                code=DatabaseErrorCode.PROFILE_NOT_FOUND,
                message=(
                    f"Failed to initialize default profile ID for '{default_profile}'"
                ),
                actual_error=str(e),
            )

    async def start_monitoring(self):
        """Start monitoring active database sessions."""
        if self._monitoring_task is None or self._monitoring_task.done():
            self._monitoring_task = asyncio.create_task(self._monitor_active_sessions())

    async def _monitor_active_sessions(self):
        while True:
            await asyncio.sleep(5)  # check every 5 secs
            with self.lock:
                if self.active_sessions:
                    current_time = time.time()
                    for session in self.active_sessions[:]:
                        session_id = id(session)
                        creation_time = self.session_creation_times.get(session_id, 0)
                        age_seconds = current_time - creation_time
                        if age_seconds > 5:  # close sessions older than 5secs
                            try:
                                await session.close()
                            except Exception:
                                pass

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

    async def create_profile(self, name: str = None) -> str:
        """Create a new profile in the database.

        Args:
            name: Profile name to create

        Returns:
            str: The created profile name

        """
        name = name or "new_profile"

        def _create():
            with self.lock:
                conn = self.pool.get_connection()
                try:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT OR IGNORE INTO profiles (name, profile_key) "
                        "VALUES (?, NULL)",
                        (name,),
                    )
                    if cursor.rowcount == 0:
                        LOGGER.error("Profile '%s' already exists", name)
                        raise DatabaseError(
                            code=DatabaseErrorCode.PROFILE_ALREADY_EXISTS,
                            message=f"Profile '{name}' already exists",
                        )
                    if not hasattr(self, "is_txn") or not self.is_txn:
                        conn.commit()
                    return name
                except Exception as e:
                    if not hasattr(self, "is_txn") or not self.is_txn:
                        conn.rollback()
                    LOGGER.error("Failed to create profile '%s': %s", name, str(e))
                    raise DatabaseError(
                        code=DatabaseErrorCode.QUERY_ERROR,
                        message=f"Failed to create profile '{name}'",
                        actual_error=str(e),
                    )
                finally:
                    self.pool.return_connection(conn)

        return await asyncio.to_thread(_create)

    async def get_profile_name(self) -> str:
        """Get the default profile name.

        Returns:
            str: Default profile name

        """
        return self.default_profile

    async def remove_profile(self, name: str) -> bool:
        """Remove a profile from the database.

        Args:
            name: Profile name to remove

        Returns:
            bool: True if removed successfully

        """

        def _remove():
            with self.lock:
                conn = self.pool.get_connection()
                try:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM profiles WHERE name = ?", (name,))
                    result = cursor.rowcount > 0
                    if not hasattr(self, "is_txn") or not self.is_txn:
                        conn.commit()
                    return result
                except Exception as e:
                    if not hasattr(self, "is_txn") or not self.is_txn:
                        conn.rollback()
                    LOGGER.error("Failed to remove profile '%s': %s", name, str(e))
                    raise DatabaseError(
                        code=DatabaseErrorCode.QUERY_ERROR,
                        message=f"Failed to remove profile '{name}'",
                        actual_error=str(e),
                    )
                finally:
                    self.pool.return_connection(conn)

        return await asyncio.to_thread(_remove)

    async def rekey(self, key_method: str = None, pass_key: str = None):
        """Rekey the database with new encryption.

        Args:
            key_method: Key method to use
            pass_key: Password key for encryption

        """

        def _rekey():
            with self.lock:
                conn = self.pool.get_connection()
                try:
                    cursor = conn.cursor()
                    cursor.execute("PRAGMA cipher_version;")
                    if not cursor.fetchone()[0]:
                        LOGGER.error("Database is not encrypted")
                        raise DatabaseError(
                            code=DatabaseErrorCode.DATABASE_NOT_ENCRYPTED,
                            message="Database is not encrypted",
                        )
                    cursor.execute(f"PRAGMA rekey = '{pass_key}'")
                    if not hasattr(self, "is_txn") or not self.is_txn:
                        conn.commit()
                    self.pool.encryption_key = pass_key
                except Exception as e:
                    if not hasattr(self, "is_txn") or not self.is_txn:
                        conn.rollback()
                    LOGGER.error("Failed to rekey database: %s", str(e))
                    raise DatabaseError(
                        code=DatabaseErrorCode.QUERY_ERROR,
                        message="Failed to rekey database",
                        actual_error=str(e),
                    )
                finally:
                    self.pool.return_connection(conn)

        await asyncio.to_thread(_rekey)

    def scan(
        self,
        profile: Optional[str],
        category: str,
        tag_filter: str | dict = None,
        offset: int = None,
        limit: int = None,
        order_by: Optional[str] = None,
        descending: bool = False,
    ) -> Generator[Entry, None, None]:
        """Scan entries in the database with filtering and pagination.

        Args:
            profile: Profile name to scan
            category: Category to scan
            tag_filter: Tag filter criteria
            offset: Offset for pagination
            limit: Limit for pagination
            order_by: Column to order by
            descending: Whether to sort descending

        Yields:
            Entry: Database entries matching criteria

        """
        handlers, _, _ = get_release(self.release_number, "sqlite")
        handler = handlers.get(category, handlers["default"])
        profile_id = self._get_profile_id(profile or self.default_profile)
        tag_query = None
        if tag_filter:
            wql_query = query_from_str(tag_filter)
            tag_query = query_to_tagquery(wql_query)
        with self.lock:
            conn = self.pool.get_connection()
            try:
                cursor = conn.cursor()
                for entry in handler.scan(
                    cursor,
                    profile_id,
                    category,
                    tag_query,
                    offset,
                    limit,
                    order_by,
                    descending,
                ):
                    yield entry
            except DatabaseError as e:
                LOGGER.error("Failed to execute scan query: %s", str(e))
                raise
            except Exception as e:
                LOGGER.error("Failed to execute scan query: %s", str(e))
                raise DatabaseError(
                    code=DatabaseErrorCode.QUERY_ERROR,
                    message="Failed to execute scan query",
                    actual_error=str(e),
                )
            finally:
                self.pool.return_connection(conn)

    def scan_keyset(
        self,
        profile: Optional[str],
        category: str,
        tag_filter: str | dict = None,
        last_id: Optional[int] = None,
        limit: int = None,
        order_by: Optional[str] = None,
        descending: bool = False,
    ) -> Generator[Entry, None, None]:
        """Scan entries using keyset pagination.

        Args:
            profile: Profile name to scan
            category: Category to scan
            tag_filter: Tag filter criteria
            last_id: Last ID for cursor-based pagination
            limit: Limit for pagination
            order_by: Column to order by
            descending: Whether to sort descending

        Yields:
            Entry: Database entries

        """
        handlers, _, _ = get_release(self.release_number, "sqlite")
        handler = handlers.get(category, handlers["default"])
        profile_id = self._get_profile_id(profile or self.default_profile)
        tag_query = None
        if tag_filter:
            wql_query = query_from_str(tag_filter)
            tag_query = query_to_tagquery(wql_query)
        with self.lock:
            conn = self.pool.get_connection()
            try:
                cursor = conn.cursor()
                for entry in handler.scan_keyset(
                    cursor,
                    profile_id,
                    category,
                    tag_query,
                    last_id,
                    limit,
                    order_by,
                    descending,
                ):
                    yield entry
            except DatabaseError as e:
                LOGGER.error("Failed to execute scan_keyset query: %s", str(e))
                raise
            except Exception as e:
                LOGGER.error("Failed to execute scan_keyset query: %s", str(e))
                raise DatabaseError(
                    code=DatabaseErrorCode.QUERY_ERROR,
                    message="Failed to execute scan_keyset query",
                    actual_error=str(e),
                )
            finally:
                self.pool.return_connection(conn)

    def session(self, profile: str = None, release_number: str = "release_0"):
        """Create a context manager for database session.

        Args:
            profile: Profile name to use
            release_number: Release number for schema versioning

        Returns:
            SqliteSession: Database session context manager

        """
        from .session import SqliteSession

        with self.lock:
            if len(self.active_sessions) >= self.max_sessions:
                LOGGER.error(
                    "Maximum number of active sessions reached: %d", self.max_sessions
                )
                raise DatabaseError(
                    code=DatabaseErrorCode.CONNECTION_POOL_EXHAUSTED,
                    message="Maximum number of active sessions reached",
                )
        sess = SqliteSession(
            self, profile or self.default_profile, False, self.release_number
        )
        with self.lock:
            self.active_sessions.append(sess)
            self.session_creation_times[id(sess)] = time.time()
        LOGGER.debug(
            "[session] Active sessions: %d, session_id=%s",
            len(self.active_sessions),
            id(sess),
        )
        return sess

    def transaction(self, profile: str = None, release_number: str = "release_0"):
        """Create a transaction context manager.

        Args:
            profile: Profile name to use
            release_number: Release number for schema versioning

        Returns:
            SqliteSession: Database transaction context manager

        """
        from .session import SqliteSession

        with self.lock:
            if len(self.active_sessions) >= self.max_sessions:
                LOGGER.error(
                    "Maximum number of active sessions reached: %d", self.max_sessions
                )
                raise DatabaseError(
                    code=DatabaseErrorCode.CONNECTION_POOL_EXHAUSTED,
                    message="Maximum number of active sessions reached",
                )
        sess = SqliteSession(
            self, profile or self.default_profile, True, self.release_number
        )
        with self.lock:
            self.active_sessions.append(sess)
            self.session_creation_times[id(sess)] = time.time()
        LOGGER.debug(
            "[session] Active sessions: %d, session_id=%s",
            len(self.active_sessions),
            id(sess),
        )
        return sess

    def close(self, remove: bool = False):
        """Close the database and optionally remove the file.

        Args:
            remove: Whether to remove the database file

        """
        try:
            # Cancel background monitoring task if running
            if self._monitoring_task and not self._monitoring_task.done():
                self._monitoring_task.cancel()
                try:
                    asyncio.get_event_loop().run_until_complete(self._monitoring_task)
                except Exception:
                    pass
                finally:
                    self._monitoring_task = None
            if self.pool:
                checkpoint_conn = None
                try:
                    checkpoint_conn = (
                        sqlite3.connect(self.path, check_same_thread=False)
                        if not self.pool.encryption_key
                        else sqlcipher.connect(self.path, check_same_thread=False)
                    )
                    if self.pool.encryption_key:
                        checkpoint_conn.execute(
                            f"PRAGMA key = '{self.pool.encryption_key}'"
                        )
                        checkpoint_conn.execute("PRAGMA cipher_migrate")
                        checkpoint_conn.execute("PRAGMA cipher_compatibility = 4")
                    cursor = checkpoint_conn.cursor()
                    cursor.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                except Exception as e:
                    LOGGER.error("WAL checkpoint failed: %s", str(e))
                finally:
                    if checkpoint_conn:
                        checkpoint_conn.close()
                try:
                    self.pool.close()
                except Exception as e:
                    LOGGER.error("Failed to close connection pool: %s", str(e))
                    raise DatabaseError(
                        code=DatabaseErrorCode.CONNECTION_ERROR,
                        message="Failed to close connection pool",
                        actual_error=str(e),
                    )
        except Exception as e:
            LOGGER.error("Failed to close database: %s", str(e))
            raise DatabaseError(
                code=DatabaseErrorCode.CONNECTION_ERROR,
                message="Failed to close database",
                actual_error=str(e),
            )
