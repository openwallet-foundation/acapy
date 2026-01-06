"""PostgreSQL normalized database implementation."""

import asyncio
import logging
import threading
import time
import urllib.parse
from typing import TYPE_CHECKING, AsyncGenerator, Optional

from psycopg import pq
from psycopg_pool import AsyncConnectionPool

from ...category_registry import get_release
from ...db_types import Entry
from ...interfaces import AbstractDatabaseStore
from ...wql_normalized.query import query_from_str
from ...wql_normalized.tags import query_to_tagquery
from ..errors import DatabaseError, DatabaseErrorCode
from .connection_pool import PostgresConnectionPool
from .schema_context import SchemaContext

if TYPE_CHECKING:
    from .backend import PostgresqlBackend

LOGGER = logging.getLogger(__name__)


ERR_NO_DB_IN_CONN_STR = "No database name specified in connection string"


class PostgresDatabase(AbstractDatabaseStore):
    """PostgreSQL database implementation for normalized storage."""

    def __init__(
        self,
        pool: AsyncConnectionPool,
        default_profile: str,
        conn_str: str,
        release_number: str = "release_0",
        max_sessions: Optional[int] = None,
        min_size: Optional[int] = None,
        max_size: Optional[int] = None,
        timeout: Optional[float] = None,
        max_idle: Optional[float] = None,
        max_lifetime: Optional[float] = None,
        schema_context: Optional[SchemaContext] = None,
        backend: Optional["PostgresqlBackend"] = None,
    ):
        """Initialize PostgreSQL database."""
        self.lock = threading.RLock()
        self.pool = pool
        self.default_profile = default_profile
        self.conn_str = conn_str
        self.release_number = release_number
        self.active_sessions = []
        self.session_creation_times = {}
        self.max_sessions = (
            max_sessions if max_sessions is not None else int(pool.max_size * 0.75)
        )
        self.default_profile_id = None
        self.min_size = min_size if min_size is not None else pool.min_size
        self.max_size = max_size if max_size is not None else pool.max_size
        self.timeout = timeout if timeout is not None else pool.timeout
        self.max_idle = max_idle if max_idle is not None else pool.max_idle
        self.max_lifetime = (
            max_lifetime if max_lifetime is not None else pool.max_lifetime
        )
        self.schema_context = (
            schema_context or SchemaContext()
        )  # Default to SchemaContext
        self.backend = backend
        self._monitoring_task: Optional[asyncio.Task] = None

    async def initialize(self):
        """Initialize the database connection."""
        try:
            self.default_profile_id = await self._get_profile_id(self.default_profile)
        except Exception as e:
            LOGGER.error(
                "Failed to initialize default profile ID for '%s': %s",
                self.default_profile,
                str(e),
            )
            raise DatabaseError(
                code=DatabaseErrorCode.PROFILE_NOT_FOUND,
                message=(
                    f"Failed to initialize default profile ID for "
                    f"'{self.default_profile}'"
                ),
                actual_error=str(e),
            )

    async def start_monitoring(self):
        """Start monitoring active sessions."""
        if self._monitoring_task is None or self._monitoring_task.done():
            self._monitoring_task = asyncio.create_task(self._monitor_active_sessions())

    async def _monitor_active_sessions(self):
        while True:
            await asyncio.sleep(5)
            with self.lock:
                if self.active_sessions:
                    current_time = time.time()
                    for session in self.active_sessions[:]:
                        session_id = id(session)
                        creation_time = self.session_creation_times.get(session_id, 0)
                        age_seconds = current_time - creation_time
                        if age_seconds > 5:
                            try:
                                await session.close()
                            except Exception as e:
                                LOGGER.warning(
                                    "[monitor] Failed to close stale session %s: %s",
                                    id(session),
                                    str(e),
                                    exc_info=True,
                                )

    async def _get_profile_id(self, profile_name: str) -> int:
        conn = await self.pool.getconn()
        try:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    (
                        f"SELECT id FROM "
                        f"{self.schema_context.qualify_table('profiles')} "
                        f"WHERE name = %s"
                    ),
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
            await self.pool.putconn(conn)

    async def create_profile(self, name: str = None) -> str:
        """Create a new profile."""
        name = name or "new_profile"
        conn = await self.pool.getconn()
        try:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    (
                        f"INSERT INTO "
                        f"{self.schema_context.qualify_table('profiles')} "
                        f"(name, profile_key) VALUES (%s, NULL) "
                        f"ON CONFLICT (name) DO NOTHING"
                    ),
                    (name,),
                )
                if cursor.rowcount == 0:
                    LOGGER.error("Profile '%s' already exists", name)
                    raise DatabaseError(
                        code=DatabaseErrorCode.PROFILE_ALREADY_EXISTS,
                        message=f"Profile '{name}' already exists",
                    )
                await conn.commit()
                return name
        except Exception as e:
            await conn.rollback()
            LOGGER.error("Failed to create profile '%s': %s", name, str(e))
            raise DatabaseError(
                code=DatabaseErrorCode.QUERY_ERROR,
                message=f"Failed to create profile '{name}'",
                actual_error=str(e),
            )
        finally:
            await self.pool.putconn(conn)

    async def get_profile_name(self) -> str:
        """Get the default profile name."""
        return self.default_profile

    async def remove_profile(self, name: str) -> bool:
        """Remove a profile."""
        conn = await self.pool.getconn()
        try:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    (
                        f"DELETE FROM "
                        f"{self.schema_context.qualify_table('profiles')} "
                        f"WHERE name = %s"
                    ),
                    (name,),
                )
                result = cursor.rowcount > 0
                await conn.commit()
                return result
        except Exception as e:
            await conn.rollback()
            LOGGER.error("Failed to remove profile '%s': %s", name, str(e))
            raise DatabaseError(
                code=DatabaseErrorCode.QUERY_ERROR,
                message=f"Failed to remove profile '{name}'",
                actual_error=str(e),
            )
        finally:
            await self.pool.putconn(conn)

    async def rekey(self, key_method: str = None, pass_key: str = None):
        """Rekey the database (not supported for PostgreSQL)."""
        LOGGER.error("Rekey not supported for PostgreSQL")
        raise DatabaseError(
            code=DatabaseErrorCode.UNSUPPORTED_OPERATION,
            message="Rekey not supported for PostgreSQL",
        )

    async def scan(
        self,
        profile: Optional[str],
        category: str,
        tag_filter: str | dict = None,
        offset: int = None,
        limit: int = None,
        order_by: Optional[str] = None,
        descending: bool = False,
    ) -> AsyncGenerator[Entry, None]:
        """Scan for entries matching criteria."""
        handlers, _, _ = get_release(self.release_number, "postgresql")

        handler = handlers.get(category, handlers["default"])
        # Update handler's schema_context to match database's schema_context
        if hasattr(handler, "set_schema_context"):
            handler.set_schema_context(self.schema_context)
        profile_id = await self._get_profile_id(profile or self.default_profile)
        tag_query = None
        if tag_filter:
            wql_query = query_from_str(tag_filter)
            tag_query = query_to_tagquery(wql_query)
        conn = await self.pool.getconn()
        try:
            async with conn.cursor() as cursor:
                async for entry in handler.scan(
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
                if conn.pgconn.transaction_status != pq.TransactionStatus.IDLE:
                    await conn.commit()
        except Exception as e:
            await conn.rollback()
            error_message = f"Failed to execute scan query: {str(e)}"
            LOGGER.error(error_message)
            raise DatabaseError(
                code=DatabaseErrorCode.QUERY_ERROR,
                message=error_message,
                actual_error=str(e),
            )
        finally:
            await self.pool.putconn(conn)

    async def scan_keyset(
        self,
        profile: Optional[str],
        category: str,
        tag_filter: str | dict = None,
        last_id: Optional[int] = None,
        limit: int = None,
        order_by: Optional[str] = None,
        descending: bool = False,
    ) -> AsyncGenerator[Entry, None]:
        """Scan using keyset pagination."""
        handlers, _, _ = get_release(self.release_number, "postgresql")

        handler = handlers.get(category, handlers["default"])
        # Update handler's schema_context to match database's schema_context
        if hasattr(handler, "set_schema_context"):
            handler.set_schema_context(self.schema_context)
        profile_id = await self._get_profile_id(profile or self.default_profile)
        tag_query = None
        if tag_filter:
            wql_query = query_from_str(tag_filter)
            tag_query = query_to_tagquery(wql_query)
        conn = await self.pool.getconn()
        try:
            async with conn.cursor() as cursor:
                async for entry in handler.scan_keyset(
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
                if conn.pgconn.transaction_status != pq.TransactionStatus.IDLE:
                    await conn.commit()
        except Exception as e:
            await conn.rollback()
            error_message = f"Failed to execute scan_keyset query: {str(e)}"
            LOGGER.error(error_message)
            raise DatabaseError(
                code=DatabaseErrorCode.QUERY_ERROR,
                message=error_message,
                actual_error=str(e),
            )
        finally:
            await self.pool.putconn(conn)

    async def session(self, profile: str = None):
        """Create a new database session."""
        from .session import PostgresSession

        with self.lock:
            if len(self.active_sessions) >= self.max_sessions:
                LOGGER.error(
                    "Maximum number of active sessions reached: %d", self.max_sessions
                )
                raise DatabaseError(
                    code=DatabaseErrorCode.CONNECTION_POOL_EXHAUSTED,
                    message="Maximum number of active sessions reached",
                )
        effective_profile = profile or self.default_profile
        cached_profile_id = (
            self.default_profile_id if effective_profile == self.default_profile else None
        )
        sess = PostgresSession(
            self, effective_profile, False, self.release_number, cached_profile_id
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

    async def transaction(self, profile: str = None):
        """Create a new database transaction."""
        from .session import PostgresSession

        with self.lock:
            if len(self.active_sessions) >= self.max_sessions:
                LOGGER.error(
                    "Maximum number of active sessions reached: %d", self.max_sessions
                )
                raise DatabaseError(
                    code=DatabaseErrorCode.CONNECTION_POOL_EXHAUSTED,
                    message="Maximum number of active sessions reached",
                )
        effective_profile = profile or self.default_profile
        cached_profile_id = (
            self.default_profile_id if effective_profile == self.default_profile else None
        )
        sess = PostgresSession(
            self, effective_profile, True, self.release_number, cached_profile_id
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

    async def close(self, remove: bool = False):
        """Close the database connection."""
        try:
            # Cancel background monitoring task if running
            if self._monitoring_task and not self._monitoring_task.done():
                self._monitoring_task.cancel()
                try:
                    await self._monitoring_task
                finally:
                    self._monitoring_task = None
            if remove:
                parsed = urllib.parse.urlparse(self.conn_str)
                target_db = parsed.path.lstrip("/")
                if not target_db:
                    raise ValueError(ERR_NO_DB_IN_CONN_STR)
                default_conn_str = self.conn_str.replace(f"/{target_db}", "/postgres")
                pool = PostgresConnectionPool(
                    conn_str=default_conn_str,
                    min_size=self.min_size,
                    max_size=self.max_size,
                    timeout=self.timeout,
                    max_idle=self.max_idle,
                    max_lifetime=self.max_lifetime,
                )
                await pool.initialize()
                try:
                    conn = await pool.getconn()
                    try:
                        await conn.rollback()
                        await conn.set_autocommit(True)
                        async with conn.cursor() as cursor:
                            await cursor.execute(
                                (
                                    "SELECT pg_terminate_backend(pg_stat_activity.pid) "
                                    "FROM pg_stat_activity "
                                    "WHERE pg_stat_activity.datname = %s "
                                    "AND pid <> pg_backend_pid()"
                                ),
                                (target_db,),
                            )
                            await cursor.execute(f"DROP DATABASE IF EXISTS {target_db}")
                    except Exception as e:
                        LOGGER.error("Failed to drop database %s: %s", target_db, str(e))
                        raise DatabaseError(
                            code=DatabaseErrorCode.CONNECTION_ERROR,
                            message=f"Failed to drop database {target_db}",
                            actual_error=str(e),
                        )
                    finally:
                        await pool.putconn(conn)
                finally:
                    await pool.close()
            await self.pool.close()
        except Exception as e:
            LOGGER.error("Failed to close database: %s", str(e))
            raise DatabaseError(
                code=DatabaseErrorCode.CONNECTION_ERROR,
                message="Failed to close database",
                actual_error=str(e),
            )
