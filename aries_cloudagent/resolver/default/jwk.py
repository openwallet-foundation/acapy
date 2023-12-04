"""did:jwk: resolver implementation."""

import re
from typing import Optional, Pattern, Sequence, Text
from aries_cloudagent.config.injection_context import InjectionContext
from aries_cloudagent.core.profile import Profile
from aries_cloudagent.resolver.base import BaseDIDResolver, ResolverType, ResolverError
from aries_cloudagent.wallet.jwt import b64_to_dict


class JwkDIDResolver(BaseDIDResolver):
    """did:jwk: resolver implementation."""

    PATTERN = re.compile(r"^did:jwk:(?P<did>.*)$")

    def __init__(self):
        """Initialize the resolver."""
        super().__init__(ResolverType.NATIVE)

    async def setup(self, context: InjectionContext):
        """Perform required setup for the resolver."""
        pass

    @property
    def supported_did_regex(self) -> Pattern:
        """Return supported DID regex."""
        return self.PATTERN

    async def _resolve(
        self,
        profile: Profile,
        did: str,
        service_accept: Optional[Sequence[Text]] = None,
    ) -> dict:
        """Resolve a DID."""
        if match := self.PATTERN.match(did):
            encoded = match.group("did")
        else:
            raise ResolverError(f"Invalid DID: {did}")

        jwk = b64_to_dict(encoded)
        doc = {
            "@context": [
                "https://www.w3.org/ns/did/v1",
                "https://w3id.org/security/suites/jws-2020/v1",
            ],
            "id": f"did:jwk:{encoded}",
            "verificationMethod": [
                {
                    "id": f"did:jwk:{encoded}#0",
                    "type": "JsonWebKey2020",
                    "controller": f"did:jwk:{encoded}",
                    "publicKeyJwk": jwk,
                }
            ],
        }

        use = jwk.get("use")
        if use == "sig":
            doc.update(
                {
                    "assertionMethod": [f"did:jwk:{encoded}#0"],
                    "authentication": [f"did:jwk:{encoded}#0"],
                    "capabilityInvocation": [f"did:jwk:{encoded}#0"],
                    "capabilityDelegation": [f"did:jwk:{encoded}#0"],
                }
            )
        elif use == "enc":
            doc.update({"keyAgreement": [f"did:jwk:{encoded}#0"]})

        return doc
