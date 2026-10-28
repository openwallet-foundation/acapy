"""Thread-safe wrapper for PyLD's global caches.

PyLD isn't fully thread-safe, so we apply a monkeypatch to wrap its module-level global
caches in a thread-safe proxy.
"""

import threading
from collections.abc import MutableMapping

import pyld.jsonld


class ThreadSafeLRUCache(MutableMapping):
    """Thread-safe proxy wrapper for `cachetools.LRUCache`."""

    def __init__(self, cache):
        """Initialize an instance of `ThreadSafeLRUCache`."""
        self._cache = cache
        self._lock = threading.Lock()

    def __getitem__(self, key):
        """See :meth:`~cachetools.LRUCache.__getitem__`."""
        with self._lock:
            return self._cache[key]

    def __setitem__(self, key, value):
        """See :meth:`~cachetools.LRUCache.__setitem__`."""
        with self._lock:
            self._cache[key] = value

    def __delitem__(self, key):
        """See :meth:`~cachetools.LRUCache.__delitem__`."""
        with self._lock:
            del self._cache[key]

    def __iter__(self):
        """See :meth:`~cachetools.LRUCache.__iter__`."""
        with self._lock:
            return iter(list(self._cache))

    def __len__(self):
        """See :meth:`~cachetools.LRUCache.__len__`."""
        with self._lock:
            return len(self._cache)

    def get(self, key, default=None):
        """See :meth:`~cachetools.LRUCache.get`."""
        with self._lock:
            return self._cache.get(key, default)

    @property
    def maxsize(self):
        """See :meth:`~cachetools.LRUCache.maxsize`."""
        return self._cache.maxsize

    @property
    def currsize(self):
        """See :meth:`~cachetools.LRUCache.currsize`."""
        with self._lock:
            return self._cache.currsize

    def clear(self):
        """See :meth:`~cachetools.LRUCache.clear`."""
        with self._lock:
            self._cache.clear()


def apply_pyld_monkeypatch():
    """Apply thread-safe proxies to PyLD's module-level global caches."""
    if not isinstance(pyld.jsonld._resolved_context_cache, ThreadSafeLRUCache):
        pyld.jsonld._resolved_context_cache = ThreadSafeLRUCache(
            pyld.jsonld._resolved_context_cache
        )
    if not isinstance(pyld.jsonld._inverse_context_cache, ThreadSafeLRUCache):
        pyld.jsonld._inverse_context_cache = ThreadSafeLRUCache(
            pyld.jsonld._inverse_context_cache
        )
