import logging
from psycopg_pool import AsyncConnectionPool
from ..errors import DatabaseError, DatabaseErrorCode

LOGGER = logging.getLogger(__name__)


class PostgresConnectionPool:
    def __init__(
        self,
        conn_str: str,
        min_size: int = 4,
        max_size: int = 100,
        timeout: float = 30.0,
        max_idle: float = 5.0,
        max_lifetime: float = 3600.0,
    ):
        self.conn_str = conn_str
        self.min_size = min_size
        self.max_size = max_size
        self.timeout = timeout
        self.max_idle = max_idle
        self.max_lifetime = max_lifetime
        self.pool = None
        self.connection_count = 0
        self.connection_ids = {}

    async def initialize(self):
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

    async def getconn(self, timeout: float = 60.0):
        try:
            conn = await self.pool.getconn(timeout=timeout)
            # Rollback any existing transaction to ensure clean state
            await conn.rollback()
            # Ensure client encoding is set to UTF-8
            await conn.execute("SET client_encoding = 'UTF8'")
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
        except Exception as e:
            LOGGER.error("Failed to retrieve connection from pool: %s", str(e))
            raise DatabaseError(
                code=DatabaseErrorCode.CONNECTION_POOL_EXHAUSTED,
                message=f"Connection pool exhausted after {timeout} seconds",
                actual_error=str(e),
            )

    # async def getconn(self, timeout: float = 60.0):
    #     LOGGER.debug("Attempting to retrieve connection from pool with timeout=%s", timeout)
    #     try:
    #         conn = await self.pool.getconn(timeout=timeout)
    #         # Check and reset transaction status
    #         LOGGER.debug("Checking transaction status for connection ID=%d, initial status=%s",
    #                     id(conn), conn.pgconn.transaction_status)
    #         if conn.pgconn.transaction_status != pq.TransactionStatus.IDLE:
    #             LOGGER.debug("Connection in non-IDLE transaction status: %s, attempting rollback",
    #                         conn.pgconn.transaction_status)
    #             try:
    #                 await conn.rollback()
    #                 LOGGER.debug("Rollback completed, new transaction status=%s",
    #                             conn.pgconn.transaction_status)
    #             except Exception as e:
    #                 LOGGER.error("Failed to rollback connection: %s", str(e))
    #                 await self.pool.putconn(conn)
    #                 raise DatabaseError(
    #                     code=DatabaseErrorCode.CONNECTION_ERROR,
    #                     message="Failed to reset connection transaction state",
    #                     actual_error=str(e)
    #                 )
    #         if conn.pgconn.transaction_status != pq.TransactionStatus.IDLE:
    #             LOGGER.error("Connection still in non-IDLE state after rollback: %s",
    #                         conn.pgconn.transaction_status)
    #             await self.pool.putconn(conn)
    #             raise DatabaseError(
    #                 code=DatabaseErrorCode.CONNECTION_ERROR,
    #                 message=f"Connection in invalid transaction state: {conn.pgconn.transaction_status}"
    #             )
    #         # Ensure client encoding is set to UTF-8
    #         LOGGER.debug("Setting client_encoding to UTF8 for connection ID=%d", id(conn))
    #         await conn.execute("SET client_encoding = 'UTF8'")
    #         conn_id = self.connection_count
    #         self.connection_ids[id(conn)] = conn_id
    #         self.connection_count += 1
    #         LOGGER.debug("Connection ID=%d retrieved from pool. Pool size: %d/%d",
    #                     conn_id, self.pool.get_stats().get("pool_available", 0), self.max_size)
    #         return conn
    #     except Exception as e:
    #         LOGGER.error("Failed to retrieve connection from pool: %s", str(e))
    #         raise DatabaseError(
    #             code=DatabaseErrorCode.CONNECTION_POOL_EXHAUSTED,
    #             message=f"Connection pool exhausted after {timeout} seconds",
    #             actual_error=str(e)
    #         )

    async def putconn(self, conn):
        try:
            # Roll back any open transactions to ensure clean state
            await conn.rollback()
            await self.pool.putconn(conn)
            conn_id = self.connection_ids.get(id(conn), -1)
            LOGGER.debug(
                "Connection ID=%d returned to pool. Pool size: %d/%d",
                conn_id,
                self.pool.get_stats().get("pool_available", 0),
                self.max_size,
            )
            del self.connection_ids[id(conn)]
        except Exception as e:
            LOGGER.error("Failed to return connection to pool: %s", str(e))
            raise DatabaseError(
                code=DatabaseErrorCode.CONNECTION_ERROR,
                message="Failed to return connection to pool",
                actual_error=str(e),
            )

    async def close(self):
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
