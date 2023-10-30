"""Resolve legacy peer DIDs.

Resolution is performed by looking up a stored DID Document.
"""

from copy import deepcopy
from dataclasses import asdict, dataclass
import logging
from typing import List, Optional, Sequence, Text, Union

from pydid import DID

from ...cache.base import BaseCache
from ...config.injection_context import InjectionContext
from ...connections.base_manager import BaseConnectionManager
from ...core.profile import Profile
from ...did.did_key import DIDKey
from ...messaging.valid import IndyDID
from ...storage.error import StorageNotFoundError
from ...wallet.key_type import ED25519
from ..base import BaseDIDResolver, DIDNotFound, ResolverType


LOGGER = logging.getLogger(__name__)


class LegacyDocCorrections:
    """Legacy peer DID document corrections.

    These corrections align the document with updated DID spec and DIDComm
    conventions. This also helps with consistent processing of DID Docs.

    Input example:
    {
      "@context": "https://w3id.org/did/v1",
      "id": "did:sov:JNKL9kJxQi5pNCfA8QBXdJ",
      "publicKey": [
        {
          "id": "did:sov:JNKL9kJxQi5pNCfA8QBXdJ#1",
          "type": "Ed25519VerificationKey2018",
          "controller": "did:sov:JNKL9kJxQi5pNCfA8QBXdJ",
          "publicKeyBase58": "AU2FFjtkVzjFuirgWieqGGqtNrAZWS9LDuB8TDp6EUrG"
        }
      ],
      "authentication": [
        {
          "type": "Ed25519SignatureAuthentication2018",
          "publicKey": "did:sov:JNKL9kJxQi5pNCfA8QBXdJ#1"
        }
      ],
      "service": [
        {
          "id": "did:sov:JNKL9kJxQi5pNCfA8QBXdJ;indy",
          "type": "IndyAgent",
          "priority": 0,
          "recipientKeys": [
            "AU2FFjtkVzjFuirgWieqGGqtNrAZWS9LDuB8TDp6EUrG"
          ],
          "routingKeys": ["9NnKFUZoYcCqYC2PcaXH3cnaGsoRfyGgyEHbvbLJYh8j"],
          "serviceEndpoint": "http://bob:3000"
        }
      ]
    }

    Output example:
    {
      "@context": "https://w3id.org/did/v1",
      "id": "did:sov:JNKL9kJxQi5pNCfA8QBXdJ",
      "verificationMethod": [
        {
          "id": "did:sov:JNKL9kJxQi5pNCfA8QBXdJ#1",
          "type": "Ed25519VerificationKey2018",
          "controller": "did:sov:JNKL9kJxQi5pNCfA8QBXdJ",
          "publicKeyBase58": "AU2FFjtkVzjFuirgWieqGGqtNrAZWS9LDuB8TDp6EUrG"
        }
      ],
      "authentication": ["did:sov:JNKL9kJxQi5pNCfA8QBXdJ#1"],
      "service": [
        {
          "id": "did:sov:JNKL9kJxQi5pNCfA8QBXdJ#didcomm",
          "type": "did-communication",
          "priority": 0,
          "recipientKeys": ["did:sov:JNKL9kJxQi5pNCfA8QBXdJ#1"],
          "routingKeys": [
              "did:key:z6Mknq3MqipEt9hJegs6J9V7tiLa6T5H5rX3fFCXksJKTuv7#z6Mknq3MqipEt9hJegs6J9V7tiLa6T5H5rX3fFCXksJKTuv7"
          ],
          "serviceEndpoint": "http://bob:3000"
        }
      ]
    }
    """

    @staticmethod
    def public_key_is_verification_method(value: dict) -> dict:
        """Replace publicKey with verificationMethod."""
        if "publicKey" in value:
            value["verificationMethod"] = value.pop("publicKey")
        return value

    @staticmethod
    def authentication_is_list_of_verification_methods_and_refs(value: dict) -> dict:
        """Update authentication to be a list of methods and references."""
        if "authentication" in value:
            modified = []
            for authn in value["authentication"]:
                if isinstance(authn, dict) and "publicKey" in authn:
                    modified.append(authn["publicKey"])
                else:
                    modified.append(authn)
                # TODO more checks?
            value["authentication"] = modified
        return value

    @staticmethod
    def didcomm_services_use_updated_conventions(value: dict) -> dict:
        """Update DIDComm services to use updated conventions."""
        if "service" in value:
            for index, service in enumerate(value["service"]):
                if "type" in service and service["type"] == "IndyAgent":
                    service["type"] = "did-communication"
                    if ";" in service["id"]:
                        service["id"] = value["id"] + f"#didcomm-{index}"
                    if "#" not in service["id"]:
                        service["id"] += f"#didcomm-{index}"
                    if "priority" in service and service["priority"] is None:
                        service.pop("priority")
        return value

    @staticmethod
    def recip_base58_to_ref(vms: List[dict], recip: str) -> str:
        """Convert base58 public key to ref."""
        for vm in vms:
            if "publicKeyBase58" in vm and vm["publicKeyBase58"] == recip:
                return vm["id"]
        return recip

    @classmethod
    def did_key_to_did_key_ref(cls, key: str):
        """Convert did:key to did:key ref."""
        # Check if key is already a ref
        if key.rfind("#") != -1:
            return key
        # Get the value after removing did:key:
        value = key.replace("did:key:", "")

        return key + "#" + value

    @classmethod
    def didcomm_services_recip_keys_are_refs_routing_keys_are_did_key_ref(
        cls,
        value: dict,
    ) -> dict:
        """Update DIDComm service recips to use refs and routingKeys to use did:key."""
        vms = value.get("verificationMethod", [])
        if "service" in value:
            for service in value["service"]:
                if "type" in service and service["type"] == "did-communication":
                    service["recipientKeys"] = [
                        cls.recip_base58_to_ref(vms, recip)
                        for recip in service.get("recipientKeys", [])
                    ]
                if "routingKeys" in service:
                    service["routingKeys"] = [
                        DIDKey.from_public_key_b58(key, ED25519).key_id
                        if "did:key:" not in key
                        else cls.did_key_to_did_key_ref(key)
                        for key in service["routingKeys"]
                    ]
        return value

    @staticmethod
    def qualified(did_or_did_url: str) -> str:
        """Make sure DID or DID URL is fully qualified."""
        if not did_or_did_url.startswith("did:"):
            return f"did:sov:{did_or_did_url}"
        return did_or_did_url

    @classmethod
    def fully_qualified_ids_and_controllers(cls, value: dict) -> dict:
        """Make sure IDs and controllers are fully qualified."""

        def _make_qualified(value: dict) -> dict:
            if "id" in value:
                ident = value["id"]
                value["id"] = cls.qualified(ident)
            if "controller" in value:
                controller = value["controller"]
                value["controller"] = cls.qualified(controller)
            return value

        value = _make_qualified(value)
        vms = []
        for verification_method in value.get("verificationMethod", []):
            vms.append(_make_qualified(verification_method))

        services = []
        for service in value.get("service", []):
            services.append(_make_qualified(service))

        auths = []
        for authn in value.get("authentication", []):
            if isinstance(authn, dict):
                auths.append(_make_qualified(authn))
            elif isinstance(authn, str):
                auths.append(cls.qualified(authn))
            else:
                raise ValueError("Unexpected authentication value type")

        value["authentication"] = auths
        value["verificationMethod"] = vms
        value["service"] = services
        return value

    @staticmethod
    def remove_verification_method(
        vms: List[dict], public_key_base58: str
    ) -> List[dict]:
        """Remove the verification method with the given key."""
        return [vm for vm in vms if vm["publicKeyBase58"] != public_key_base58]

    @classmethod
    def remove_routing_keys_from_verification_method(cls, value: dict) -> dict:
        """Remove routing keys from verification methods.

        This was an old convention; routing keys were added to the public keys
        of the doc even though they're usually not owned by the doc sender.

        This correction should be applied before turning the routing keys into
        did keys.
        """
        vms = value.get("verificationMethod", [])
        for service in value.get("service", []):
            if "routingKeys" in service:
                for routing_key in service["routingKeys"]:
                    vms = cls.remove_verification_method(vms, routing_key)
        value["verificationMethod"] = vms
        return value

    @classmethod
    def apply(cls, value: dict) -> dict:
        """Apply all corrections to the given DID document."""
        value = deepcopy(value)
        for correction in (
            cls.public_key_is_verification_method,
            cls.authentication_is_list_of_verification_methods_and_refs,
            cls.fully_qualified_ids_and_controllers,
            cls.didcomm_services_use_updated_conventions,
            cls.remove_routing_keys_from_verification_method,
            cls.didcomm_services_recip_keys_are_refs_routing_keys_are_did_key_ref,
        ):
            value = correction(value)

        return value


@dataclass
class RetrieveResult:
    """Entry in the peer DID cache."""

    is_local: bool
    doc: Optional[dict] = None


class LegacyPeerDIDResolver(BaseDIDResolver):
    """Resolve legacy peer DIDs."""

    def __init__(self):
        """Initialize the resolver instance."""
        super().__init__(ResolverType.NATIVE)

    async def setup(self, context: InjectionContext):
        """Perform required setup for the resolver."""

    async def _fetch_did_document(self, profile: Profile, did: str) -> RetrieveResult:
        """Fetch DID from wallet if available.

        This is the method to be used with fetch_did_document to enable caching.
        """
        conn_mgr = BaseConnectionManager(profile)
        if did.startswith("did:sov:"):
            did = did[8:]
        try:
            doc, _ = await conn_mgr.fetch_did_document(did)
            LOGGER.debug("Fetched doc %s", doc)
            to_cache = RetrieveResult(True, doc=doc.serialize())
        except StorageNotFoundError:
            LOGGER.debug("Failed to fetch doc for did %s", did)
            to_cache = RetrieveResult(False)

        return to_cache

    async def fetch_did_document(
        self, profile: Profile, did: str, *, ttl: Optional[int] = None
    ):
        """Fetch DID from wallet if available.

        Return value is cached.
        """
        cache_key = f"resolver::LegacyPeerDIDResolver::{did}"
        cache = profile.inject_or(BaseCache)
        if cache:
            async with cache.acquire(cache_key) as entry:
                if entry.result:
                    result = RetrieveResult(**entry.result)
                else:
                    result = await self._fetch_did_document(profile, did)
                    await entry.set_result(asdict(result), ttl or self.DEFAULT_TTL)
        else:
            result = await self._fetch_did_document(profile, did)

        return result

    async def supports(self, profile: Profile, did: str) -> bool:
        """Return whether this resolver supports the given DID.

        This resolver resolves unqualified DIDs and dids prefixed with
        `did:sov:`.

        These DIDs have the unfortunate characteristic of overlapping with what
        ACA-Py uses for DIDs written to Indy ledgers. This means that we will
        need to attempt to resolve but defer to the Indy resolver if we don't
        find anything locally. This has the side effect that this resolver will
        never raise DIDNotFound since it won't even be selected for resolution
        unless we have the DID in our wallet.

        This will check if the DID matches the IndyDID regex. If it does,
        attempt a lookup in the wallet for a document. If found, return True.
        Else, return False.
        """
        LOGGER.debug("Checking if resolver supports DID %s", did)
        if IndyDID.PATTERN.match(did):
            LOGGER.debug("DID is valid IndyDID %s", did)
            result = await self.fetch_did_document(profile, did)
            return result.is_local
        else:
            return False

    async def resolve(
        self,
        profile: Profile,
        did: Union[str, DID],
        service_accept: Optional[Sequence[Text]] = None,
    ) -> dict:
        """Resolve a Legacy Peer DID to a DID document by fetching from the wallet.

        This overrides the default resolve method so we can take care of caching
        ourselves since we use it for the supports method as well.
        """
        return await self._resolve(profile, str(did), service_accept)

    async def _resolve(
        self,
        profile: Profile,
        did: str,
        service_accept: Optional[Sequence[Text]] = None,
    ) -> dict:
        """Resolve Legacy Peer DID to a DID document by fetching from the wallet.

        By the time this resolver is selected, it should be impossible for it
        to raise a DIDNotFound.
        """
        result = await self.fetch_did_document(profile, did)
        if result.is_local:
            assert result.doc
            return LegacyDocCorrections.apply(result.doc)
        else:
            # This should be impossible because of the checks in supports
            raise DIDNotFound(f"DID not found: {did}")
