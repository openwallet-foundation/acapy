"""HTTP Universal DID Resolver."""

import os
from typing import Sequence

import aiohttp
import yaml

from ...core.profile import Profile
from ..base import BaseDIDResolver, DIDNotFound, ResolverError, ResolverType
from ..did import DID
from ..diddoc import ResolvedDIDDoc


class HTTPUniversalDIDResolver(BaseDIDResolver):
    """Universal DID Resolver with HTTP bindings."""

    def __init__(self):
        """Initialize HTTPUniversalDIDResolver."""
        super().__init__(ResolverType.NON_NATIVE)
        self._endpoint = None
        self._supported_methods = None

    async def setup(self, profile: Profile):
        """Preform setup, populate supported method list, configuration."""
        config_file = os.environ.get("UNI_RESOLVER_CONFIG", "universal_resolver.yml")
        self.configure(yaml.load(config_file))

    def configure(self, configuration: dict):
        """Configure this instance of the resolver from configuration dict."""
        self._endpoint = configuration["endpoint"]
        self._supported_methods = configuration["methods"]

    @property
    def supported_methods(self) -> Sequence[str]:
        """Return supported methods.

        By determining methods from config file, we preserve the ability to not
        use the universal resolver for a given method, even if the universal
        is capable of resolving that method.
        """
        return self._supported_methods

    async def _resolve(self, profile: Profile, did: DID) -> ResolvedDIDDoc:
        """Resolve DID through remote universal resolver."""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self._endpoint}/{did}") as resp:
                if resp.status == 200:
                    doc = await resp.json()
                    return ResolvedDIDDoc(doc["didDocument"])
                if resp.status == 404:
                    raise DIDNotFound(f"{did} not found by {self.__class__.__name__}")

                raise ResolverError(
                    f"Unexecpted status from universal resolver ({resp.status}): ",
                    await resp.text()
                )
