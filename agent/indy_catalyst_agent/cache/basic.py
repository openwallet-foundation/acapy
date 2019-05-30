"""Basic in-memory cache implementation"""

from datetime import datetime, timedelta

from typing import Any, Text

from .base import BaseCache


class BasicCache(BaseCache):
    """Basic in-memory cache class"""

    def __init__(self):
        """
        Initialize a `BasicCache` instance.
        """

        # looks like { "key": { "expires": <epoch timestamp>, "value": <val> } }
        self._cache = {}

    def _remove_expired_cache_items(self):
        """
        Removes all expired items from cache.
        """
        for key in self._cache:
            cache_item_expiry = self._cache["key"]["expires"]
            now = datetime.now().timestamp()
            if now >= cache_item_expiry:
                del self._cache["key"]

    async def get(self, key: Text):
        """
        Gets an item from the cache

        Args:
            key: the key to retrieve an item for

        Returns:
            The record found or `None`

        """
        self._remove_expired_cache_items()
        return self._cache.get(key)

    async def set(self, key: Text, value: Any, ttl: int = 0):
        """
        Adds an item to the cache with an optional ttl.
        Overwrites existing cache entries

        Args:
            key: the key to set an item for
            value: the value to store in the cache
            ttl: number of seconds that the record should persist

        """
        self._remove_expired_cache_items()
        now = datetime.now()
        expires = now + timedelta(seconds=ttl)
        expires_ts = expires.timestamp()

        self._cache[key] = {"expires": expires_ts, "value": value}

    async def flush(self):
        """
        Removes all items from the cache
        """

        self._cache = {}
