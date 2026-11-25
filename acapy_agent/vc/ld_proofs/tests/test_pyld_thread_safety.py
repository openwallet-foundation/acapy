"""Regression test for concurrent PyLD use from the PyLD thread executor.

PyLD keeps module-level ``cachetools.LRUCache`` instances that are not thread-safe.
Without ``apply_pyld_monkeypatch``, this test reliably fails with ``KeyError`` or
``RuntimeError: OrderedDict mutated during iteration`` raised from those caches.
"""

import asyncio
import collections
import sys

import pytest
from pyld import jsonld

from ....utils.threadsafelrucache import ThreadSafeLRUCache, apply_pyld_monkeypatch
from ..pyld_util import _PYLD_EXECUTOR, run_sync

# Enough distinct contexts to keep both caches evicting entries
NUM_CONTEXTS = 4 * max(
    jsonld.RESOLVED_CONTEXT_CACHE_MAX_SIZE, jsonld.INVERSE_CONTEXT_CACHE_MAX_SIZE
)
NUM_OPERATIONS = 2000


def _context_url(index: int) -> str:
    return f"http://ctx.example/{index}"


def _local_loader(url: str, options: dict) -> dict:
    index = url.rsplit("/", 1)[1]
    return {
        "contentType": "application/ld+json",
        "contextUrl": None,
        "documentUrl": url,
        "document": {
            "@context": {
                f"p{index}": f"http://example.org/p{index}",
                "name": "http://schema.org/name",
            }
        },
    }


def _expand_and_compact(index: int) -> None:
    context = _context_url(index)
    doc = {"@context": context, f"p{index}": "x", "name": "n"}
    options = {"documentLoader": _local_loader}
    expanded = jsonld.expand(doc, options)
    compacted = jsonld.compact(expanded, context, options)
    assert compacted.get(f"p{index}") == "x", compacted


@pytest.fixture
def patched_pyld_caches(monkeypatch):
    # Registering the current caches makes monkeypatch restore them afterwards
    monkeypatch.setattr(jsonld, "_resolved_context_cache", jsonld._resolved_context_cache)
    monkeypatch.setattr(jsonld, "_inverse_context_cache", jsonld._inverse_context_cache)
    apply_pyld_monkeypatch()
    yield


@pytest.fixture
def fast_thread_switching():
    # Switch threads very often so cache races show up within a short run
    original = sys.getswitchinterval()
    sys.setswitchinterval(1e-6)
    yield
    sys.setswitchinterval(original)


def test_monkeypatch_wraps_caches_once(patched_pyld_caches):
    resolved = jsonld._resolved_context_cache
    inverse = jsonld._inverse_context_cache
    assert isinstance(resolved, ThreadSafeLRUCache)
    assert isinstance(inverse, ThreadSafeLRUCache)

    apply_pyld_monkeypatch()

    assert jsonld._resolved_context_cache is resolved
    assert jsonld._inverse_context_cache is inverse


async def test_concurrent_pyld_operations(patched_pyld_caches, fast_thread_switching):
    assert _PYLD_EXECUTOR._max_workers > 1, "test requires a multi-threaded executor"

    results = await asyncio.gather(
        *(run_sync(_expand_and_compact, i % NUM_CONTEXTS) for i in range(NUM_OPERATIONS)),
        return_exceptions=True,
    )

    errors = collections.Counter(
        f"{type(r).__name__}: {r}"[:120] for r in results if isinstance(r, Exception)
    )
    assert not errors, (
        f"{sum(errors.values())} of {NUM_OPERATIONS} concurrent PyLD operations "
        f"failed: {errors.most_common(3)}"
    )
