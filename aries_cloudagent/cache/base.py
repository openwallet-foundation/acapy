"""Abstract base classes for cache."""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Optional, Sequence, Text, Union

from ..core.error import BaseError


class CacheError(BaseError):
    """Base class for cache-related errors."""


class BaseCache(ABC):
    """Abstract cache interface."""

    def __init__(self):
        """Initialize the cache instance."""
        self._key_locks = {}

    @abstractmethod
    async def get(self, key: Text):
        """
        Get an item from the cache.

        Args:
            key: the key to retrieve an item for

        Returns:
            The record found or `None`

        """

    @abstractmethod
    async def set(
        self, keys: Union[Text, Sequence[Text]], value: Any, ttl: Optional[int] = None
    ):
        """
        Add an item to the cache with an optional ttl.

        Args:
            keys: the key or keys for which to set an item
            value: the value to store in the cache
            ttl: number of second that the record should persist

        """

    @abstractmethod
    async def clear(self, key: Text):
        """
        Remove an item from the cache, if present.

        Args:
            key: the key to remove

        """

    @abstractmethod
    async def flush(self):
        """Remove all items from the cache."""

    def acquire(self, key: Text):
        """Acquire a lock on a given cache key."""
        result = CacheKeyLock(self, key)
        first = self._key_locks.setdefault(key, result)
        if first is not result:
            result.parent = first
        return result

    def release(self, key: Text):
        """Release the lock on a given cache key."""
        if key in self._key_locks:
            del self._key_locks[key]

    def __repr__(self) -> str:
        """Human readable representation of this instance."""
        return "<{}>".format(self.__class__.__name__)


class CacheKeyLock:
    """
    A lock on a particular cache key.

    Used to prevent multiple async threads from generating
    or querying the same semi-expensive data. Not thread safe.
    """

    def __init__(self, cache: BaseCache, key: Text):
        """Initialize the key lock."""
        self.cache = cache
        self.exception: BaseException = None
        self.key = key
        self.released = False
        self._future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._parent: "CacheKeyLock" = None

    @property
    def done(self) -> bool:
        """Accessor for the done state."""
        return self._future.done()

    @property
    def future(self) -> asyncio.Future:
        """Fetch the result in the form of an awaitable future."""
        return self._future

    @property
    def result(self) -> Any:
        """Fetch the current result, if any."""
        if self.done:
            return self._future.result()

    @property
    def parent(self) -> "CacheKeyLock":
        """Accessor for the parent key lock, if any."""
        return self._parent

    @parent.setter
    def parent(self, parent: "CacheKeyLock"):
        """Setter for the parent lock."""
        self._parent = parent
        parent._future.add_done_callback(self._handle_parent_done)

    def _handle_parent_done(self, fut: asyncio.Future):
        """Handle completion of parent's future."""
        result = fut.result()
        if result:
            self._future.set_result(fut.result())

    async def set_result(self, value: Any, ttl: Optional[int] = None):
        """Set the result, updating the cache and any waiters."""
        if self.done and value:
            raise CacheError("Result already set")
        self._future.set_result(value)
        if not self._parent or self._parent.done:
            await self.cache.set(self.key, value, ttl)

    def __await__(self):
        """Wait for a result to be produced."""
        return (yield from self._future)

    async def __aenter__(self):
        """Async context manager entry."""
        result = None
        if self.parent:
            result = await self.parent
            if result:
                await self  # wait for parent's done handler to complete
        if not result:
            found = await self.cache.get(self.key)
            if found:
                self._future.set_result(found)
        return self

    def release(self):
        """Release the cache lock."""
        if not self.parent and not self.released:
            self.cache.release(self.key)
            self.released = True

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Async context manager exit.

        `None` is returned to any waiters if no value is produced.
        """
        if exc_val:
            self.exception = exc_val
        if not self.done:
            self._future.set_result(None)
        self.release()

    def __del__(self):
        """Handle deletion."""
        self.release()
