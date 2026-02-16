"""Module docstring."""

import asyncio
import logging
import urllib.parse

from psycopg_pool import AsyncConnectionPool

from ..errors import DatabaseError, DatabaseErrorCode

LOGGER = logging.getLogger(__name__)


class PostgresConnectionPool:
    """Connection pool manager for PostgreSQL databases."""

    def __init__(
        self,
        conn_str: str,
        min_size: int = 4,
        max_size: int = 100,
        timeout: float = 30.0,
        max_idle: float = 5.0,
        max_lifetime: float = 3600.0,
    ):
        """Initialize PostgreSQL connection pool."""
        # Sanitize connection string by removing admin parameters
        self.conn_str = self._sanitize_conn_str(conn_str)
        self.min_size = min_size
        self.max_size = max_size
        self.timeout = timeout
        self.max_idle = max_idle
        self.max_lifetime = max_lifetime
        self.pool = None
        self.connection_count = 0
        self.connection_ids = {}

    def _sanitize_conn_str(self, conn_str: str) -> str:
        """Remove admin parameters from connection string that psycopg doesn't accept."""
        parsed = urllib.parse.urlparse(conn_str)
        query_params = urllib.parse.parse_qs(parsed.query)

        # Remove admin parameters
        admin_params = ["admin_account", "admin_password"]
        for param in admin_params:
            query_params.pop(param, None)

        # Rebuild query string
        new_query = urllib.parse.urlencode(query_params, doseq=True)

        # Rebuild URL
        sanitized = parsed._replace(query=new_query).geturl()
        return sanitized

    async def initialize(self):
        """Initialize the connection pool."""
        try:
            self.pool = AsyncConnectionPool(
                conninfo=self.conn_str,
                min_size=self.min_size,
                max_size=self.max_size,
                timeout=self.timeout,
                max_idle=self.max_idle,
                max_lifetime=self.max_lifetime,
                kwargs={"options": "-c client_encoding=UTF8"},  # Ensure UTF-8 encoding
            )
            await self.pool.open()  # Explicitly open pool to avoid deprecation warning
            await self.pool.wait()
            LOGGER.debug("Connection pool initialized with %d connections", self.min_size)
        except Exception as e:
            LOGGER.error("Failed to initialize connection pool: %s", str(e))
            raise DatabaseError(
                code=DatabaseErrorCode.CONNECTION_ERROR,
                message="Failed to initialize connection pool",
                actual_error=str(e),
            )

    async def getconn(self):
        """Get a connection from the pool."""
        try:
            conn = await asyncio.wait_for(self.pool.getconn(), timeout=60.0)
            # Rollback any existing transaction to ensure clean state
            # This ensures the connection is in IDLE state before returning
            await conn.rollback()
            # Note: UTF-8 encoding is already set at pool creation via kwargs
            # (options: -c client_encoding=UTF8), so no need to SET it here.
            # Executing SET here would start an implicit transaction and add latency.
            conn_id = self.connection_count
            self.connection_ids[id(conn)] = conn_id
            self.connection_count += 1
            LOGGER.debug(
                "Connection ID=%d retrieved from pool. Pool size: %d/%d",
                conn_id,
                self.pool.get_stats().get("pool_available", 0),
                self.max_size,
            )
            return conn
        except asyncio.TimeoutError as e:
            LOGGER.error("Failed to retrieve connection from pool: %s", str(e))
            raise DatabaseError(
                code=DatabaseErrorCode.CONNECTION_POOL_EXHAUSTED,
                message="Connection pool exhausted after 60.0 seconds",
                actual_error=str(e),
            )
        except Exception as e:
            LOGGER.error("Failed to retrieve connection from pool: %s", str(e))
            raise DatabaseError(
                code=DatabaseErrorCode.CONNECTION_POOL_EXHAUSTED,
                message="Connection pool exhausted",
                actual_error=str(e),
            )

    async def putconn(self, conn):
        """Return a connection to the pool."""
        try:
            # Roll back any open transactions to ensure clean state
            await conn.rollback()
            await self.pool.putconn(conn)
            conn_id = self.connection_ids.pop(id(conn), -1)
            LOGGER.debug(
                "Connection ID=%d returned to pool. Pool size: %d/%d",
                conn_id,
                self.pool.get_stats().get("pool_available", 0),
                self.max_size,
            )
        except Exception as e:
            LOGGER.error("Failed to return connection to pool: %s", str(e))
            raise DatabaseError(
                code=DatabaseErrorCode.CONNECTION_ERROR,
                message="Failed to return connection to pool",
                actual_error=str(e),
            )

    async def close(self):
        """Close the connection pool."""
        try:
            await self.pool.close()
            self.connection_ids.clear()
            LOGGER.debug("Connection pool closed")
        except Exception as e:
            LOGGER.error("Failed to close connection pool: %s", str(e))
            raise DatabaseError(
                code=DatabaseErrorCode.CONNECTION_ERROR,
                message="Failed to close connection pool",
                actual_error=str(e),
            )
