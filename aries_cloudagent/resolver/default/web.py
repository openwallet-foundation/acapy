"""Web DID Resolver."""

import urllib.parse

from typing import Optional, Pattern, Sequence, Text

import aiohttp

from pydid import DID, DIDDocument

from ...config.injection_context import InjectionContext
from ...core.profile import Profile
from ...messaging.valid import DIDWeb

from ..base import (
    BaseDIDResolver,
    DIDNotFound,
    ResolverError,
    ResolverType,
)


class WebDIDResolver(BaseDIDResolver):
    """Web DID Resolver."""

    def __init__(self):
        """Initialize Web DID Resolver."""
        super().__init__(ResolverType.NATIVE)

    async def setup(self, context: InjectionContext):
        """Perform required setup for Web DID resolution."""

    @property
    def supported_did_regex(self) -> Pattern:
        """Return supported_did_regex of Web DID Resolver."""
        return DIDWeb.PATTERN

    def __transform_to_url(self, did):
        """
        Transform did to url.

        according to
        https://w3c-ccg.github.io/did-method-web/#read-resolve
        """

        as_did = DID(did)
        method_specific_id = as_did.method_specific_id
        if ":" in method_specific_id:
            # contains path
            url = method_specific_id.replace(":", "/")
        else:
            # bare domain needs /.well-known path
            url = method_specific_id + "/.well-known"

        # Support encoded ports (See: https://github.com/w3c-ccg/did-method-web/issues/7)
        url = urllib.parse.unquote(url)

        return "https://" + url + "/did.json"

    async def _resolve(
        self,
        profile: Profile,
        did: str,
        service_accept: Optional[Sequence[Text]] = None,
    ) -> dict:
        """Resolve did:web DIDs."""

        url = self.__transform_to_url(did)
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    try:
                        # Validate DIDDoc with pyDID
                        did_doc = DIDDocument.from_json(await response.text())
                        return did_doc.serialize()
                    except Exception as err:
                        raise ResolverError(
                            "Response was incorrectly formatted"
                        ) from err
                if response.status == 404:
                    raise DIDNotFound(f"No document found for {did}")
                raise ResolverError(
                    "Could not find doc for {}: {}".format(did, await response.text())
                )
