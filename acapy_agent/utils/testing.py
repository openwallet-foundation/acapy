"""Utilities for testing."""

import functools
import inspect
from typing import Optional

import pytest
from pyld.jsonld import JsonLdError
from uuid_utils import uuid4

from ..askar.profile import AskarProfile
from ..askar.profile_anon import AskarAnonCredsProfile
from ..askar.store import AskarStoreConfig
from ..config.injection_context import InjectionContext


async def create_test_profile(
    settings: Optional[dict] = None, context: Optional[InjectionContext] = None
) -> AskarProfile | AskarAnonCredsProfile:
    """Create a profile for testing."""
    if not settings:
        settings = {
            "wallet.type": "askar",
            "auto_provision": True,
            "wallet.key": "5BngFuBpS4wjFfVFCtPqoix3ZXG2XR8XJ7qosUzMak7R",
            "wallet.key_derivation_method": "RAW",
        }
    _id = settings.get("wallet.id", str(uuid4()))
    settings["wallet.id"] = _id
    """Create a profile for testing."""
    store_config = AskarStoreConfig(
        {
            "name": _id,
            "key": "5BngFuBpS4wjFfVFCtPqoix3ZXG2XR8XJ7qosUzMak7R",
            "key_derivation_method": "RAW",
            "auto_recreate": True,
        }
    )
    if not context:
        context = InjectionContext(
            settings=settings,
        )
    opened = await store_config.open_store(provision=True, in_memory=True)

    if settings.get("wallet.type") == "askar-anoncreds":
        return AskarAnonCredsProfile(
            opened=opened,
            context=context,
        )
    return AskarProfile(
        opened=opened,
        context=context,
    )


def skip_on_jsonld_url_error(test_func):
    """Decorator to skip tests when they fail due to JSON-LD URL resolution issues.

    This catches specific errors related to w3.org/w3id.org URL dereferencing failures
    that occur when external JSON-LD context URLs are not accessible. This prevents
    test failures due to temporary network issues or external service downtime.

    Args:
        test_func: The test function to decorate

    Returns:
        Wrapped test function that skips on JSON-LD URL resolution errors
    """

    def _handle_jsonld_error(e):
        """Check if exception is a JSON-LD URL resolution error and skip if so."""

        if isinstance(e, JsonLdError):
            error_str = str(e)
            # Check for specific JSON-LD URL resolution error patterns
            if any(
                pattern in error_str
                for pattern in [
                    "Dereferencing a URL did not result in a valid JSON-LD object",
                    "Could not retrieve a JSON-LD document from the URL",
                    "loading remote context failed",
                    "Could not process context before compaction",
                    "Could not expand input before compaction",
                    "Could not convert input to RDF dataset before normalization",
                    "Could not expand input before serialization to RDF",
                ]
            ) and any(
                url in error_str
                for url in [
                    "w3id.org/citizenship",
                    "w3id.org/security",
                    "w3.org/2018/credentials",
                    "w3.org/ns/",
                ]
            ):
                pytest.skip(
                    f"Skipping test due to JSON-LD URL resolution error: {error_str}"
                )

        # Re-raise if it's not a URL resolution error we want to skip
        raise

    @functools.wraps(test_func)
    async def async_wrapper(*args, **kwargs):
        try:
            return await test_func(*args, **kwargs)
        except Exception as e:
            _handle_jsonld_error(e)

    @functools.wraps(test_func)
    def sync_wrapper(*args, **kwargs):
        try:
            return test_func(*args, **kwargs)
        except Exception as e:
            _handle_jsonld_error(e)

    # Return appropriate wrapper based on whether the function is async
    if inspect.iscoroutinefunction(test_func):
        return async_wrapper
    else:
        return sync_wrapper
