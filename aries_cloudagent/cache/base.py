"""Abstract base classes for cache."""

from abc import ABC, abstractmethod
from typing import Any, Sequence, Text, Union


class BaseCache(ABC):
    """Abstract cache interface."""

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
    async def set(self, keys: Union[Text, Sequence[Text]], value: Any, ttl: int = None):
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

    def __repr__(self) -> str:
        """Human readable representation of `BaseStorageRecordSearch`."""
        return "<{}>".format(self.__class__.__name__)
