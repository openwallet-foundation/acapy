"""Cache for multitenancy profiles."""

import logging
from collections import OrderedDict
from typing import Optional
from weakref import WeakValueDictionary

from ..core.profile import Profile

LOGGER = logging.getLogger(__name__)


class ProfileCache:
    """Profile cache that caches based on LRU strategy."""

    def __init__(self, capacity: int):
        """Initialize ProfileCache.

        Args:
            capacity: The capacity of the cache. If capacity is exceeded
                      profiles are closed.
        """

        LOGGER.debug(f"Profile cache initialized with capacity {capacity}")

        self._cache: OrderedDict[str, Profile] = OrderedDict()
        self.profiles: WeakValueDictionary[str, Profile] = WeakValueDictionary()
        self.capacity = capacity

    def _cleanup(self):
        """Prune cache until size matches defined capacity."""
        if len(self._cache) > self.capacity:
            LOGGER.debug(
                f"Profile limit of {self.capacity} reached."
                " Evicting least recently used profiles..."
            )
            while len(self._cache) > self.capacity:
                key, _ = self._cache.popitem(last=False)
                LOGGER.debug(f"Evicted profile with key {key}")

    def get(self, key: str) -> Optional[Profile]:
        """Get profile with associated key from cache.

        If a profile is open but has been evicted from the cache, this will
        reinsert the profile back into the cache. This prevents attempting to
        open a profile that is already open. Triggers clean up.

        Args:
            key (str): the key to get the profile for.

        Returns:
            Optional[Profile]: Profile if found in cache.

        """
        value = self.profiles.get(key)
        if value:
            if key not in self._cache:
                LOGGER.debug(
                    f"Rescuing profile {key} from eviction from cache; profile "
                    "will be reinserted into cache"
                )
                self._cache[key] = value
            self._cache.move_to_end(key)
            self._cleanup()

        return value

    def has(self, key: str) -> bool:
        """Check whether there is a profile with associated key in the cache.

        Args:
            key (str): the key to check for a profile

        Returns:
            bool: Whether the key exists in the cache

        """
        return key in self.profiles

    def put(self, key: str, value: Profile) -> None:
        """Add profile with associated key to the cache.

        If new profile exceeds the cache capacity least recently used profiles
        that are not used will be removed from the cache.

        Args:
            key (str): the key to set
            value (Profile): the profile to set
        """

        # Profiles are responsible for cleaning up after themselves when they
        # fall out of scope. Previously the cache needed to create a finalizer.
        # value.finalzer()

        # Keep track of currently opened profiles using weak references
        self.profiles[key] = value

        # Strong reference to profile to hold open until evicted
        LOGGER.debug(f"Setting profile with id {key} in profile cache")
        self._cache[key] = value

        # Refresh profile livliness
        self._cache.move_to_end(key)
        self._cleanup()

    def remove(self, key: str):
        """Remove profile with associated key from the cache.

        Args:
            key (str): The key to remove from the cache.
        """
        del self.profiles[key]
        del self._cache[key]
