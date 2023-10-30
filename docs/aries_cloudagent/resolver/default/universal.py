"""HTTP Universal DID Resolver."""

import logging
import re
from typing import Iterable, Optional, Pattern, Sequence, Union, Text

import aiohttp

from ...config.injection_context import InjectionContext
from ...core.profile import Profile
from ..base import BaseDIDResolver, DIDNotFound, ResolverError, ResolverType

LOGGER = logging.getLogger(__name__)
DEFAULT_ENDPOINT = "https://dev.uniresolver.io/1.0"


def _compile_supported_did_regex(patterns: Iterable[Union[str, Pattern]]):
    """Create regex from list of regex."""
    return re.compile(
        "(?:"
        + "|".join(
            [
                pattern.pattern if isinstance(pattern, Pattern) else pattern
                for pattern in patterns
            ]
        )
        + ")"
    )


class UniversalResolver(BaseDIDResolver):
    """Universal DID Resolver with HTTP bindings."""

    def __init__(
        self,
        *,
        endpoint: Optional[str] = None,
        supported_did_regex: Optional[Pattern] = None,
        bearer_token: Optional[str] = None,
    ):
        """Initialize UniversalResolver."""
        super().__init__(ResolverType.NON_NATIVE)
        self._endpoint = endpoint
        self._supported_did_regex = supported_did_regex

        self.__default_headers = (
            {"Authorization": f"Bearer {bearer_token}"} if bearer_token else {}
        )

    async def setup(self, context: InjectionContext):
        """Perform setup, populate supported method list, configuration."""

        # configure endpoint
        endpoint = context.settings.get_str("resolver.universal")
        if endpoint == "DEFAULT" or not endpoint:
            endpoint = DEFAULT_ENDPOINT
        self._endpoint = endpoint

        # configure authorization
        token = context.settings.get_str("resolver.universal.token")
        self.__default_headers = {"Authorization": f"Bearer {token}"} if token else {}

        # configure supported methods
        supported = context.settings.get("resolver.universal.supported")
        if supported is None:
            supported_did_regex = await self._get_supported_did_regex()
        else:
            supported_did_regex = _compile_supported_did_regex(supported)

        self._supported_did_regex = supported_did_regex

    @property
    def supported_did_regex(self) -> Pattern:
        """Return supported methods regex."""
        if not self._supported_did_regex:
            raise ResolverError("Resolver has not been set up")

        return self._supported_did_regex

    async def _resolve(
        self,
        _profile: Profile,
        did: str,
        service_accept: Optional[Sequence[Text]] = None,
    ) -> dict:
        """Resolve DID through remote universal resolver."""

        async with aiohttp.ClientSession(headers=self.__default_headers) as session:
            async with session.get(f"{self._endpoint}/identifiers/{did}") as resp:
                if resp.status == 200:
                    doc = await resp.json()
                    did_doc = doc["didDocument"]
                    LOGGER.info("Retrieved doc: %s", did_doc)
                    return did_doc
                if resp.status == 404:
                    raise DIDNotFound(f"{did} not found by {self.__class__.__name__}")

                text = await resp.text()
                raise ResolverError(
                    f"Unexpected status from universal resolver ({resp.status}): {text}"
                )

    async def _fetch_resolver_props(self) -> dict:
        """Retrieve universal resolver properties."""
        async with aiohttp.ClientSession(headers=self.__default_headers) as session:
            async with session.get(f"{self._endpoint}/properties/") as resp:
                if 200 <= resp.status < 400:
                    return await resp.json()
                raise ResolverError(
                    "Failed to retrieve resolver properties: " + await resp.text()
                )

    async def _get_supported_did_regex(self) -> Pattern:
        props = await self._fetch_resolver_props()
        return _compile_supported_did_regex(
            driver["http"]["pattern"] for driver in props.values()
        )
