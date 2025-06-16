"""A module for handling asynchronous locks using SQLite and portalocker."""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import portalocker

from .async_lock import AsyncLock

LOGGER = logging.getLogger(__name__)


class SqliteAsyncLock(AsyncLock):
    """A class to handle asynchronous locking using SQLite.

    Note: This implementation uses file-based locks with portalocker.
    It is suitable for single-node applications where SQLite is used as the storage
    backend.

    It does not support distributed locking across multiple nodes. Clustered
    environments should use the currently supported postgres lock or
    implement a custom distributed lock mechanism.
    """

    @classmethod
    def create(cls, connection_uri: Optional[str] = None):
        """Create a Lock instance with a SQLite connection."""
        cls.lock_dir = Path("/tmp/sqlite_locks")
        cls.lock_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _lock_file_path(lock_dir: Path, lock_name: str) -> Path:
        return lock_dir / f"{lock_name}.lock"

    @asynccontextmanager
    async def lock(self, lock_key: str, timeout: int = 10):
        """Acquire a lock with the given key using SQLite and portalocker."""
        loop = asyncio.get_running_loop()
        file_path = self._lock_file_path(self.lock_dir, lock_key)

        lock = portalocker.Lock(
            file_path,
            mode="a+",
            flags=portalocker.LOCK_EX,  # No fail_when_locked
        )

        async def acquire():
            await loop.run_in_executor(None, lock.acquire)

        try:
            await asyncio.wait_for(acquire(), timeout=timeout)
            LOGGER.debug(f"[LOCK ACQUIRED] Key: {lock_key}")
            yield
        except asyncio.TimeoutError:
            LOGGER.warning(f"Timeout acquiring lock: {lock_key}")
            raise TimeoutError(f"Timeout acquiring lock: {lock_key}")
        finally:
            try:
                await loop.run_in_executor(None, lock.release)
                LOGGER.debug(f"[LOCK RELEASED] Key: {lock_key}")
            except Exception:
                LOGGER.warning(f"Failed to release lock: {lock_key}")
