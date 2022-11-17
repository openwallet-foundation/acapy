"""Basic in-memory cache implementation."""

import time
from typing import Any, Sequence, Text, Union

from .base import BaseCache


class InMemoryCache(BaseCache):
    """Basic in-memory cache class."""

    def __init__(self):
        """Initialize a `InMemoryCache` instance."""
        super().__init__()
        # looks like { "key": { "expires": <epoch timestamp>, "value": <val> } }
        self._cache = {}

    def _remove_expired_cache_items(self):
        """Remove all expired items from cache."""
        for key, val in self._cache.copy().items():  # iterate copy, del from original
            cache_item_expiry = val["expires"]
            if cache_item_expiry is None:
                continue
            now = time.perf_counter()
            if now >= cache_item_expiry:
                del self._cache[key]

    async def get(self, key: Text):
        """
        Get an item from the cache.

        Args:
            key: the key to retrieve an item for

        Returns:
            The record found or `None`

        """
        self._remove_expired_cache_items()
        return self._cache.get(key)["value"] if self._cache.get(key) else None

    async def set(self, keys: Union[Text, Sequence[Text]], value: Any, ttl: int = None):
        """
        Add an item to the cache with an optional ttl.

        Overwrites existing cache entries.

        Args:
            keys: the key or keys for which to set an item
            value: the value to store in the cache
            ttl: number of seconds that the record should persist

        """
        self._remove_expired_cache_items()
        expires_ts = time.perf_counter() + ttl if ttl else None
        for key in [keys] if isinstance(keys, Text) else keys:
            self._cache[key] = {"expires": expires_ts, "value": value}

    async def clear(self, key: Text):
        """
        Remove an item from the cache, if present.

        Args:
            key: the key to remove

        """
        if key in self._cache:
            del self._cache[key]

    async def flush(self):
        """Remove all items from the cache."""

        self._cache = {}
