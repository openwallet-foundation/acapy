"""Indy DID Resolver.

Resolution is performed using the IndyLedger class.
"""
from typing import Sequence

from ...config.injection_context import InjectionContext
from ...core.profile import Profile
from ...ledger.indy import IndySdkLedger
from ...ledger.base import BaseLedger
from ...ledger.error import LedgerError
from ..base import BaseDIDResolver, DIDNotFound, ResolverError, ResolverType
from ..did import DID
from ..diddoc import ResolvedDIDDoc


class NoIndyLedger(ResolverError):
    """Raised when there is no indy ledger instance configured."""


class IndyDIDResolver(BaseDIDResolver):
    """Indy DID Resolver."""

    VERIFICATION_METHOD_TYPE = "Ed25519VerificationKey2018"

    def __init__(self):
        """Initialize Indy Resolver."""
        super().__init__(ResolverType.NATIVE)

    async def setup(self, context: InjectionContext):
        """Perform required setup for Indy DID resolution."""

    @property
    def supported_methods(self) -> Sequence[str]:
        """Return supported methods of Indy DID Resolver."""
        return ["sov"]

    async def _resolve(self, profile: Profile, did: DID) -> ResolvedDIDDoc:
        """Resolve an indy DID."""
        ledger = profile.inject(BaseLedger, required=False)
        if not ledger or not isinstance(ledger, IndySdkLedger):
            raise NoIndyLedger("No Indy ledger instance is configured.")

        try:
            async with ledger:
                recipient_key = await ledger.get_key_for_did(str(did))
                endpoint = await ledger.get_endpoint_for_did(str(did))
        except LedgerError as err:
            raise DIDNotFound(f"DID {did} could not be resolved") from err

        doc = {
            "id": str(did),
            "verificationMethod": [
                {
                    "id": did.ref(1),
                    "type": self.VERIFICATION_METHOD_TYPE,
                    "controller": str(did),
                    "publicKeyBase58": recipient_key,
                }
            ],
            "authentication": [did.ref(1)],
        }

        if endpoint:
            doc["service"] = [{
                "id": did.ref(ResolvedDIDDoc.AGENT_SERVICE_TYPE),
                "type": ResolvedDIDDoc.AGENT_SERVICE_TYPE,
                "priority": 0,
                "recipientKeys": [did.ref(1)],
                "routingKeys": [],
                "serviceEndpoint": endpoint,
            }]

        return ResolvedDIDDoc(doc)
