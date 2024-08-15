"""Adapters for DMP library."""

import logging
from typing import Optional, cast

from aries_askar import Key

try:
    from didcomm_messaging import SecretsManager
    from didcomm_messaging.crypto.backend.askar import AskarSecretKey
    from didcomm_messaging.resolver import DIDResolver as DMPResolver
except ModuleNotFoundError as err:
    raise ImportError("Install the didcommv2 extra to use this module.") from err

from ..askar.profile import AskarProfileSession
from ..core.error import BaseError
from ..core.profile import Profile, ProfileSession
from ..resolver.did_resolver import DIDResolver

LOGGER = logging.getLogger(__name__)


class DMPAdapterError(BaseError):
    """Raised on general errors from DMP Adapters."""


class ResolverAdapter(DMPResolver):
    """Adapter for ACA-Py resolver to DMP Resolver."""

    def __init__(self, profile: Profile, resolver: DIDResolver):
        """Init the adapter."""
        self.profile = profile
        self.resolver = resolver

    async def resolve(self, did: str) -> dict:
        """Resolve a DID."""
        return await self.resolver.resolve(self.profile, did)

    async def is_resolvable(self, did: str) -> bool:
        """Check to see if a DID is resolvable."""
        for resolver in self.resolver.resolvers:
            if await resolver.supports(self.profile, did):
                return True

        return False


class SecretsAdapterError(DMPAdapterError):
    """Errors from DMP Secrets Adapter."""


class SecretsAdapter(SecretsManager[AskarSecretKey]):
    """Adapter for providing a secrets manager compatible with DMP."""

    def __init__(self, session: ProfileSession):
        """Init the adapter."""
        self.session = session

    async def get_secret_by_kid(self, kid: str) -> Optional[AskarSecretKey]:
        """Get a secret key by its ID."""
        if not isinstance(self.session, AskarProfileSession):
            raise SecretsAdapterError(
                "ACA-Py's implementation of DMP only supports an Askar backend"
            )

        LOGGER.debug("GETTING SECRET BY KID: %s", kid)
        key_entries = await self.session.handle.fetch_all_keys(
            tag_filter={"kid": kid}, limit=2
        )
        if len(key_entries) > 1:
            raise SecretsAdapterError(f"More than one key found with kid {kid}")

        entry = key_entries[0]
        if entry:
            key = cast(Key, entry.key)
            return AskarSecretKey(key=key, kid=kid)

        LOGGER.debug("RETURNING NONE")
        return None
