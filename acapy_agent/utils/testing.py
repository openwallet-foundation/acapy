"""Utilities for testing."""

from typing import Optional
from uuid import uuid4

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
