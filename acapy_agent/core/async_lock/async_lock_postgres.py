"""Advisory Lock Service for PostgreSQL."""

import asyncio
import hashlib
import logging
import struct
import time
from contextlib import asynccontextmanager
from typing import Optional

import psycopg
from psycopg.rows import tuple_row
from psycopg.sql import SQL, Identifier

from .async_lock import AsyncLock

LOGGER = logging.getLogger(__name__)


class PostgresAsyncLock(AsyncLock):
    """A class to manage distributed advisory locks in PostgreSQL.

    Note: This implementation uses PostgreSQL's advisory locks
    to provide a distributed locking mechanism suitable for clustered environments.
    It is designed to work with PostgreSQL databases and requires a valid connection URI
    that it acquires from the provided storage configuration.
    """

    @classmethod
    async def create(cls, connection_uri: Optional[str] = None):
        """Create a Lock instance with a PostgreSQL connection."""
        cls.connection_uri = connection_uri
        await cls._create_db_if_not_exists(cls.connection_uri)

    @staticmethod
    async def _create_db_if_not_exists(base_uri: str, dbname="lock_db"):
        async with await psycopg.AsyncConnection.connect(
            base_uri, autocommit=True
        ) as conn:
            async with conn.cursor(row_factory=tuple_row) as cur:
                await cur.execute(
                    "SELECT 1 FROM pg_database WHERE datname = %s", (dbname,)
                )
                exists = await cur.fetchone()

                if not exists:
                    LOGGER.info(f"Creating database '{dbname}'...")
                    await cur.execute(
                        SQL("CREATE DATABASE {}").format(Identifier(dbname))
                    )
                else:
                    LOGGER.debug(f"Database '{dbname}' already exists.")

    def _make_pg_lock_key(self, value) -> int:
        h = hashlib.sha256(str(value).encode()).digest()
        return struct.unpack("q", h[:8])[0]  # signed 64-bit int

    @asynccontextmanager
    async def lock(self, lock_key: str, timeout: int = 10):
        """Acquires a PostgreSQL advisory lock for the given key.

        Times out after `timeout` seconds if the lock isn't available.
        """
        lock_key = self._make_pg_lock_key(lock_key)
        async with await psycopg.AsyncConnection.connect(
            self.connection_uri, autocommit=True
        ) as conn:
            async with conn.cursor() as cur:
                start = time.time()
                acquired = False

                while time.time() - start < timeout:
                    await cur.execute("SELECT pg_try_advisory_lock(%s);", (lock_key,))
                    acquired = (await cur.fetchone())[0]

                    if acquired:
                        LOGGER.debug(f"[LOCK ACQUIRED] Key: {lock_key}")
                        break

                    await asyncio.sleep(1)

                if not acquired:
                    raise TimeoutError(
                        f"Could not acquire advisory lock {lock_key} within {timeout} seconds."
                    )

                try:
                    yield
                finally:
                    await cur.execute("SELECT pg_advisory_unlock(%s);", (lock_key,))
                    LOGGER.debug(f"[LOCK RELEASED] Key: {lock_key}")
