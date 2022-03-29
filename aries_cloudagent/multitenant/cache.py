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

        self.profiles: OrderedDict[str, Profile] = OrderedDict()
        self._open_profiles: WeakValueDictionary[str, Profile] = WeakValueDictionary()
        self.capacity = capacity

    def _cleanup(self):
        """Prune cache until size matches defined capacity."""
        if len(self.profiles) > self.capacity:
            LOGGER.debug(
                f"Profile limit of {self.capacity} reached."
                " Evicting least recently used profiles..."
            )
            while len(self.profiles) > self.capacity:
                key, _ = self.profiles.popitem(last=False)
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
        if key not in self._open_profiles:
            return None
        else:
            value = self._open_profiles[key]
            if key not in self.profiles:
                LOGGER.debug(
                    f"Rescuing profile {key} from eviction from cache; profile "
                    "will be reinserted into cache"
                )
                self.profiles[key] = value
            self.profiles.move_to_end(key)
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
        value.finalizer()
        self._open_profiles[key] = value
        self.profiles[key] = value
        LOGGER.debug(f"Setting profile with id {key} in profile cache")
        self.profiles.move_to_end(key)
        self._cleanup()

    def remove(self, key: str):
        """Remove profile with associated key from the cache.

        Args:
            key (str): The key to remove from the cache.
        """
        del self.profiles[key]
