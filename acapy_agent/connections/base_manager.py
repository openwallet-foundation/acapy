"""Class to provide some common utilities.

For Connection, DIDExchange and OutOfBand Manager.
"""

import json
import logging
import warnings
from typing import Dict, List, Optional, Sequence, Text, Tuple, Union

import pydid
from base58 import b58decode
from did_peer_2 import KeySpec, generate
from did_peer_4 import encode, long_to_short
from did_peer_4.input_doc import KeySpec as KeySpec_DP4
from did_peer_4.input_doc import input_doc_from_keys_and_services
from pydid import BaseDIDDocument as ResolvedDocument
from pydid import DIDCommService, VerificationMethod
from pydid.verification_method import (
    Ed25519VerificationKey2018,
    Ed25519VerificationKey2020,
    JsonWebKey2020,
    Multikey,
)

from ..cache.base import BaseCache
from ..config.base import InjectionError
from ..core.error import BaseError
from ..core.profile import Profile
from ..did.did_key import DIDKey
from ..multitenant.base import BaseMultitenantManager
from ..protocols.coordinate_mediation.v1_0.models.mediation_record import MediationRecord
from ..protocols.coordinate_mediation.v1_0.route_manager import RouteManager
from ..protocols.didexchange.v1_0.message_types import ARIES_PROTOCOL as CONN_PROTO
from ..protocols.discovery.v2_0.manager import V20DiscoveryMgr
from ..protocols.out_of_band.v1_0.messages.invitation import InvitationMessage
from ..resolver.base import ResolverError
from ..resolver.did_resolver import DIDResolver
from ..storage.base import BaseStorage
from ..storage.error import StorageDuplicateError, StorageNotFoundError
from ..storage.record import StorageRecord
from ..transport.inbound.receipt import MessageReceipt
from ..utils.multiformats import multibase, multicodec
from ..wallet.base import BaseWallet
from ..wallet.crypto import create_keypair, seed_to_did
from ..wallet.did_info import INVITATION_REUSE_KEY, DIDInfo, KeyInfo
from ..wallet.did_method import PEER2, PEER4, SOV, DIDMethod
from ..wallet.error import WalletNotFoundError
from ..wallet.key_type import ED25519, X25519
from ..wallet.util import b64_to_bytes, bytes_to_b58
from .models.conn_record import ConnRecord
from .models.connection_target import ConnectionTarget
from .models.diddoc import DIDDoc, PublicKey, PublicKeyType, Service


class BaseConnectionManagerError(BaseError):
    """BaseConnectionManager error."""


class BaseConnectionManager:
    """Class to provide utilities regarding connection_targets."""

    RECORD_TYPE_DID_DOC = "did_doc"
    RECORD_TYPE_DID_KEY = "did_key"

    def __init__(self, profile: Profile):
        """Initialize a BaseConnectionManager.

        Args:
            profile (Profile): The profile object associated with this connection manager.

        """
        self._profile = profile
        self._route_manager = profile.inject(RouteManager)
        self._logger = logging.getLogger(__name__)

    @staticmethod
    def _key_info_to_multikey(key_info: KeyInfo) -> str:
        """Convert a KeyInfo to a multikey."""
        if key_info.key_type == ED25519:
            return multibase.encode(
                multicodec.wrap("ed25519-pub", b58decode(key_info.verkey)), "base58btc"
            )
        elif key_info.key_type == X25519:
            return multibase.encode(
                multicodec.wrap("x25519-pub", b58decode(key_info.verkey)), "base58btc"
            )
        else:
            raise BaseConnectionManagerError(
                "Unsupported key type. Could not convert to multikey."
            )

    def long_did_peer_to_short(self, long_did: str) -> str:
        """Convert did:peer:4 long format to short format and return."""

        short_did_peer = long_to_short(long_did)
        return short_did_peer

    async def long_did_peer_4_to_short(self, long_dp4: str) -> str:
        """Convert did:peer:4 long format to short format and store in wallet."""

        async with self._profile.session() as session:
            wallet = session.inject(BaseWallet)
            long_dp4_info = await wallet.get_local_did(long_dp4)

        short_did_peer_4 = long_to_short(long_dp4)
        did_info = DIDInfo(
            did=short_did_peer_4,
            method=PEER4,
            verkey=long_dp4_info.verkey,
            metadata={},
            key_type=ED25519,
        )
        async with self._profile.session() as session:
            wallet = session.inject(BaseWallet)
            await wallet.store_did(did_info)
        return did_info.did

    async def create_did_peer_4(
        self,
        svc_endpoints: Optional[Sequence[str]] = None,
        mediation_records: Optional[List[MediationRecord]] = None,
        metadata: Optional[Dict] = None,
    ) -> DIDInfo:
        """Create a did:peer:4 DID for a connection.

        Args:
            svc_endpoints (Optional[Sequence[str]]): Custom endpoints for the
                DID Document.
            mediation_records (Optional[List[MediationRecord]]): The records for
                mediation that contain routing keys and service endpoint.
            metadata (Optional[Dict]): Additional metadata for the DID.

        Returns:
            DIDInfo: The new `DIDInfo` instance representing the created DID.
        """
        routing_keys: List[str] = []
        if mediation_records:
            for mediation_record in mediation_records:
                (
                    mediator_routing_keys,
                    endpoint,
                ) = await self._route_manager.routing_info(
                    self._profile, mediation_record
                )
                routing_keys = [*routing_keys, *(mediator_routing_keys or [])]
                if endpoint:
                    svc_endpoints = [endpoint]

        services = []
        for index, endpoint in enumerate(svc_endpoints or []):
            services.append(
                {
                    "id": f"#didcomm-{index}",
                    "type": "did-communication",
                    "recipientKeys": ["#key-0"],
                    "routingKeys": routing_keys,
                    "serviceEndpoint": endpoint,
                    "priority": index,
                }
            )

        async with self._profile.session() as session:
            wallet = session.inject(BaseWallet)
            key = await wallet.create_key(ED25519)
            key_spec = KeySpec_DP4(
                multikey=self._key_info_to_multikey(key),
                relationships=["authentication", "keyAgreement"],
            )
            input_doc = input_doc_from_keys_and_services(
                keys=[key_spec], services=services
            )
            did = encode(input_doc)

            did_metadata = metadata if metadata else {}
            did_info = DIDInfo(
                did=did,
                method=PEER4,
                verkey=key.verkey,
                metadata=did_metadata,
                key_type=ED25519,
            )
            await wallet.store_did(did_info)

        return did_info

    async def create_did_peer_2(
        self,
        svc_endpoints: Optional[Sequence[str]] = None,
        mediation_records: Optional[List[MediationRecord]] = None,
        metadata: Optional[Dict] = None,
    ) -> DIDInfo:
        """Create a did:peer:2 DID for a connection.

        Args:
            svc_endpoints (Optional[Sequence[str]]): Custom endpoints for the
                DID Document.
            mediation_records (Optional[List[MediationRecord]]): The records for
                mediation that contain routing keys and service endpoint.
            metadata (Optional[Dict]): Additional metadata for the DID.

        Returns:
            DIDInfo: The new `DIDInfo` instance representing the created DID.
        """
        routing_keys: List[str] = []
        if mediation_records:
            for mediation_record in mediation_records:
                (
                    mediator_routing_keys,
                    endpoint,
                ) = await self._route_manager.routing_info(
                    self._profile, mediation_record
                )
                routing_keys = [*routing_keys, *(mediator_routing_keys or [])]
                if endpoint:
                    svc_endpoints = [endpoint]

        services = []
        for index, endpoint in enumerate(svc_endpoints or []):
            services.append(
                {
                    "id": f"#didcomm-{index}",
                    "type": "did-communication",
                    "priority": index,
                    "recipientKeys": ["#key-1"],
                    "routingKeys": routing_keys,
                    "serviceEndpoint": endpoint,
                }
            )
            if self._profile.settings.get("experiment.didcomm_v2"):
                services.append(
                    {
                        "id": f"#service-{index}",
                        "type": "DIDCommMessaging",
                        "serviceEndpoint": {
                            "uri": endpoint,
                            "accept": ["didcomm/v2"],
                            "routingKeys": routing_keys,
                        },
                    }
                )

        async with self._profile.session() as session:
            wallet = session.inject(BaseWallet)
            key = await wallet.create_key(ED25519)
            xk = await wallet.create_key(X25519)

            did = generate(
                [
                    KeySpec.verification(self._key_info_to_multikey(key)),
                    KeySpec.key_agreement(self._key_info_to_multikey(xk)),
                ],
                services,
            )

            did_metadata = metadata if metadata else {}
            did_info = DIDInfo(
                did=did,
                method=PEER2,
                verkey=key.verkey,
                metadata=did_metadata,
                key_type=ED25519,
            )
            await wallet.store_did(did_info)
            await wallet.assign_kid_to_key(key.verkey, f"{did}#key-1")
            await wallet.assign_kid_to_key(xk.verkey, f"{did}#key-2")

        return did_info

    async def fetch_invitation_reuse_did(
        self,
        did_method: DIDMethod,
    ) -> Optional[DIDInfo]:
        """Fetch a DID from the wallet to use across multiple invitations.

        Args:
            did_method: The DID method used (e.g. PEER2 or PEER4)

        Returns:
            The `DIDInfo` instance, or "None" if no DID is found
        """
        did_info = None
        async with self._profile.session() as session:
            wallet = session.inject(BaseWallet)
            # TODO Iterating through all DIDs is problematic
            did_list = await wallet.get_local_dids()
            for did in did_list:
                if did.method == did_method and INVITATION_REUSE_KEY in did.metadata:
                    return did
        return did_info

    async def create_did_document(
        self,
        did_info: DIDInfo,
        svc_endpoints: Optional[Sequence[str]] = None,
        mediation_records: Optional[List[MediationRecord]] = None,
    ) -> DIDDoc:
        """Create our DID doc for a given DID.

        This method is deprecated and will be removed.

        Args:
            did_info (DIDInfo): The DID information (DID and verkey) used in the
                connection.
            svc_endpoints (Optional[Sequence[str]]): Custom endpoints for the
                DID Document.
            mediation_records (Optional[List[MediationRecord]]): The records for
                mediation that contain routing keys and service endpoints.

        Returns:
            DIDDoc: The prepared `DIDDoc` instance.

        """
        warnings.warn("create_did_document is deprecated and will be removed soon")
        did_doc = DIDDoc(did=did_info.did)
        did_controller = did_info.did
        did_key = did_info.verkey
        pk = PublicKey(
            did_info.did,
            "1",
            did_key,
            PublicKeyType.ED25519_SIG_2018,
            did_controller,
            True,
        )
        did_doc.set(pk)

        routing_keys: List[str] = []
        if mediation_records:
            for mediation_record in mediation_records:
                (
                    mediator_routing_keys,
                    endpoint,
                ) = await self._route_manager.routing_info(
                    self._profile, mediation_record
                )
                routing_keys = [*routing_keys, *(mediator_routing_keys or [])]
                if endpoint:
                    svc_endpoints = [endpoint]

        for endpoint_index, svc_endpoint in enumerate(svc_endpoints or []):
            endpoint_ident = "indy" if endpoint_index == 0 else f"indy{endpoint_index}"
            service = Service(
                did_info.did,
                endpoint_ident,
                "IndyAgent",
                [pk],
                routing_keys,
                svc_endpoint,
            )
            did_doc.set(service)

        return did_doc

    async def store_did_document(self, value: Union[DIDDoc, dict]):
        """Store a DID document.

        Args:
            value: The `DIDDoc` instance to persist
        """
        if isinstance(value, DIDDoc):
            did = value.did
            doc = value.to_json()
        else:
            did = value["id"]
            doc = json.dumps(value)

        # Special case: we used to store did:sov dids as unqualified.
        # For backwards compatibility, we'll strip off the prefix.
        if did.startswith("did:sov:"):
            did = did[8:]

        self._logger.debug("Storing DID document for %s: %s", did, doc)

        try:
            stored_doc, record = await self.fetch_did_document(did)
        except StorageNotFoundError:
            record = StorageRecord(self.RECORD_TYPE_DID_DOC, doc, {"did": did})
            async with self._profile.session() as session:
                storage: BaseStorage = session.inject(BaseStorage)
                await storage.add_record(record)
        else:
            async with self._profile.session() as session:
                storage: BaseStorage = session.inject(BaseStorage)
                await storage.update_record(record, doc, {"did": did})

        await self.remove_keys_for_did(did)
        await self.record_keys_for_resolvable_did(did)

    async def add_key_for_did(self, did: str, key: str):
        """Store a verkey for lookup against a DID.

        Args:
            did: The DID to associate with this key
            key: The verkey to be added
        """
        record = StorageRecord(self.RECORD_TYPE_DID_KEY, key, {"did": did, "key": key})
        async with self._profile.session() as session:
            storage: BaseStorage = session.inject(BaseStorage)
            try:
                await storage.find_record(self.RECORD_TYPE_DID_KEY, {"key": key})
            except StorageNotFoundError:
                await storage.add_record(record)
            except StorageDuplicateError:
                self._logger.warning(
                    "Key already associated with DID: %s; this is likely caused by "
                    "routing keys being erroneously stored in the past",
                    key,
                )

    async def find_did_for_key(self, key: str) -> str:
        """Find the DID previously associated with a key.

        Args:
            key: The verkey to look up
        """
        async with self._profile.session() as session:
            storage: BaseStorage = session.inject(BaseStorage)
            record = await storage.find_record(self.RECORD_TYPE_DID_KEY, {"key": key})
        ret_did = record.tags["did"]
        return ret_did

    async def remove_keys_for_did(self, did: str):
        """Remove all keys associated with a DID.

        Args:
            did: The DID for which to remove keys
        """
        async with self._profile.session() as session:
            storage: BaseStorage = session.inject(BaseStorage)
            await storage.delete_all_records(self.RECORD_TYPE_DID_KEY, {"did": did})

    async def resolve_didcomm_services(
        self, did: str, service_accept: Optional[Sequence[Text]] = None
    ) -> Tuple[ResolvedDocument, List[DIDCommService]]:
        """Resolve a DIDComm services for a given DID."""
        if not did.startswith("did:"):
            # DID is bare indy "nym"
            # prefix with did:sov: for backwards compatibility
            did = f"did:sov:{did}"

        resolver = self._profile.inject(DIDResolver)
        try:
            doc_dict: dict = await resolver.resolve(self._profile, did, service_accept)
            doc: ResolvedDocument = pydid.deserialize_document(doc_dict, strict=True)
        except (ResolverError, ValueError) as error:
            raise BaseConnectionManagerError("Failed to resolve DID services") from error

        if not doc.service:
            raise BaseConnectionManagerError(
                "Cannot connect via DID that has no associated services"
            )

        didcomm_services = sorted(
            [service for service in doc.service if isinstance(service, DIDCommService)],
            key=lambda service: service.priority,
        )

        return doc, didcomm_services

    async def verification_methods_for_service(
        self, doc: ResolvedDocument, service: DIDCommService
    ) -> Tuple[List[VerificationMethod], List[VerificationMethod]]:
        """Dereference recipient and routing keys.

        Returns verification methods for a DIDComm service to enable extracting
        key material.
        """
        resolver = self._profile.inject(DIDResolver)
        recipient_keys: List[VerificationMethod] = [
            await resolver.dereference_verification_method(
                self._profile, url, document=doc
            )
            for url in service.recipient_keys
        ]
        routing_keys: List[VerificationMethod] = [
            await resolver.dereference_verification_method(
                self._profile, url, document=doc
            )
            for url in service.routing_keys
        ]
        return recipient_keys, routing_keys

    async def resolve_invitation(
        self, did: str, service_accept: Optional[Sequence[Text]] = None
    ) -> Tuple[str, List[str], List[str]]:
        """Resolve invitation with the DID Resolver.

        Args:
            did (str): Document ID to resolve.
            service_accept (Optional[Sequence[Text]]): List of accepted service types.

        Returns:
            Tuple[str, List[str], List[str]]: A tuple containing the endpoint,
                recipient keys, and routing keys.

        Raises:
            BaseConnectionManagerError: If the public DID has no associated
                DIDComm services.
        """
        doc, didcomm_services = await self.resolve_didcomm_services(did, service_accept)
        if not didcomm_services:
            raise BaseConnectionManagerError(
                "Cannot connect via public DID that has no associated DIDComm services"
            )

        first_didcomm_service, *_ = didcomm_services

        endpoint = str(first_didcomm_service.service_endpoint)
        recipient_keys, routing_keys = await self.verification_methods_for_service(
            doc, first_didcomm_service
        )

        return (
            endpoint,
            [self._extract_key_material_in_base58_format(key) for key in recipient_keys],
            [self._extract_key_material_in_base58_format(key) for key in routing_keys],
        )

    async def record_keys_for_resolvable_did(self, did: str):
        """Record the keys for a public DID.

        This is required to correlate sender verkeys back to a connection.
        """
        doc, didcomm_services = await self.resolve_didcomm_services(did)
        for service in didcomm_services:
            recips, _ = await self.verification_methods_for_service(doc, service)
            for recip in recips:
                await self.add_key_for_did(
                    did, self._extract_key_material_in_base58_format(recip)
                )

    async def resolve_connection_targets(
        self,
        did: str,
        sender_verkey: Optional[str] = None,
        their_label: Optional[str] = None,
    ) -> List[ConnectionTarget]:
        """Resolve connection targets for a DID."""
        self._logger.debug("Resolving connection targets for DID %s", did)
        doc, didcomm_services = await self.resolve_didcomm_services(did)
        self._logger.debug("Resolved DID document: %s", doc)
        self._logger.debug("Resolved DIDComm services: %s", didcomm_services)
        targets = []
        for service in didcomm_services:
            try:
                recips, routing = await self.verification_methods_for_service(
                    doc, service
                )
                endpoint = str(service.service_endpoint)
                targets.append(
                    ConnectionTarget(
                        did=doc.id,
                        endpoint=endpoint,
                        label=their_label,
                        recipient_keys=[
                            self._extract_key_material_in_base58_format(key)
                            for key in recips
                        ],
                        routing_keys=[
                            self._extract_key_material_in_base58_format(key)
                            for key in routing
                        ],
                        sender_key=sender_verkey,
                    )
                )
            except ResolverError:
                self._logger.exception(
                    "Failed to resolve service details while determining "
                    "connection targets; skipping service"
                )
                continue

        return targets

    @staticmethod
    def _extract_key_material_in_base58_format(method: VerificationMethod) -> str:
        if isinstance(method, Ed25519VerificationKey2018):
            return method.material
        elif isinstance(method, Ed25519VerificationKey2020):
            raw_data = multibase.decode(method.material)
            if len(raw_data) == 32:  # No multicodec prefix
                return bytes_to_b58(raw_data)
            else:
                codec, key = multicodec.unwrap(raw_data)
                if codec == multicodec.multicodec("ed25519-pub"):
                    return bytes_to_b58(key)
                else:
                    raise BaseConnectionManagerError(
                        f"Key type {type(method).__name__} "
                        f"with multicodec value {codec} is not supported"
                    )

        elif isinstance(method, JsonWebKey2020):
            if method.public_key_jwk.get("kty") == "OKP":
                return bytes_to_b58(b64_to_bytes(method.public_key_jwk.get("x"), True))
            else:
                raise BaseConnectionManagerError(
                    f"Key type {type(method).__name__} "
                    f"with kty {method.public_key_jwk.get('kty')} is not supported"
                )
        elif isinstance(method, Multikey):
            codec, key = multicodec.unwrap(multibase.decode(method.material))
            if codec != multicodec.multicodec("ed25519-pub"):
                raise BaseConnectionManagerError(
                    "Expected ed25519 multicodec, got: %s", codec
                )
            return bytes_to_b58(key)
        else:
            raise BaseConnectionManagerError(
                f"Key type {type(method).__name__} is not supported"
            )

    async def _fetch_connection_targets_for_invitation(
        self,
        connection: ConnRecord,
        invitation: InvitationMessage,
        sender_verkey: str,
    ) -> Sequence[ConnectionTarget]:
        """Get a list of connection targets for an invitation.

        This method extracts target information for either a connection or out-of-band
            (OOB) invitation.

        Args:
            connection (ConnRecord): The connection record associated with the invitation.
            invitation (InvitationMessage): The connection
                or OOB invitation retrieved from the connection record.
            sender_verkey (str): The sender's verification key.

        Returns:
            Sequence[ConnectionTarget]: A list of `ConnectionTarget` objects
                representing the connection targets for the invitation.
        """
        assert invitation.services, "Schema requires services in invitation"
        oob_service_item = invitation.services[0]
        if isinstance(oob_service_item, str):
            (
                endpoint,
                recipient_keys,
                routing_keys,
            ) = await self.resolve_invitation(oob_service_item)

        else:
            endpoint = oob_service_item.service_endpoint
            recipient_keys = [
                DIDKey.from_did(k).public_key_b58 for k in oob_service_item.recipient_keys
            ]
            routing_keys = [
                DIDKey.from_did(k).public_key_b58 for k in oob_service_item.routing_keys
            ]

        return [
            ConnectionTarget(
                did=connection.their_did,
                endpoint=endpoint,
                label=invitation.label if invitation else None,
                recipient_keys=recipient_keys,
                routing_keys=routing_keys,
                sender_key=sender_verkey,
            )
        ]

    async def _fetch_targets_for_connection_in_progress(
        self, connection: ConnRecord, sender_verkey: str
    ) -> Sequence[ConnectionTarget]:
        """Get a list of connection targets from an incomplete `ConnRecord`.

        This covers retrieving targets for connections that are still in the
        process of bootstrapping. This includes connections that are in states
        invitation-received or request-received.

        Args:
            connection: The connection record (with associated `DIDDoc`)
                used to generate the connection target
            sender_verkey: The verkey we are using
        Returns:
            A list of `ConnectionTarget` objects
        """
        if (
            connection.invitation_msg_id
            or connection.invitation_key
            or not connection.their_did
        ):  # invitation received or sending request to invitation
            async with self._profile.session() as session:
                invitation = await connection.retrieve_invitation(session)
            targets = await self._fetch_connection_targets_for_invitation(
                connection,
                invitation,
                sender_verkey,
            )
        else:  # sending implicit request
            # request is implicit; did isn't set if we've received an
            # invitation, only the invitation key
            (
                endpoint,
                recipient_keys,
                routing_keys,
            ) = await self.resolve_invitation(connection.their_did)
            targets = [
                ConnectionTarget(
                    did=connection.their_did,
                    endpoint=endpoint,
                    label=None,
                    recipient_keys=recipient_keys,
                    routing_keys=routing_keys,
                    sender_key=sender_verkey,
                )
            ]

        return targets

    async def fetch_connection_targets(
        self, connection: ConnRecord
    ) -> Sequence[ConnectionTarget]:
        """Get a list of connection targets from a `ConnRecord`.

        Args:
            connection: The connection record (with associated `DIDDoc`)
                used to generate the connection target
        """

        if not connection.my_did:
            self._logger.debug("No local DID associated with connection")
            return []

        async with self._profile.session() as session:
            wallet = session.inject(BaseWallet)
            my_info = await wallet.get_local_did(connection.my_did)

        if (
            ConnRecord.State.get(connection.state)
            in (ConnRecord.State.INVITATION, ConnRecord.State.REQUEST)
            and ConnRecord.Role.get(connection.their_role) is ConnRecord.Role.RESPONDER
        ):  # invitation received or sending request
            return await self._fetch_targets_for_connection_in_progress(
                connection, my_info.verkey
            )

        if not connection.their_did:
            self._logger.debug("No target DID associated with connection")
            return []

        return await self.resolve_connection_targets(
            connection.their_did, my_info.verkey, connection.their_label
        )

    async def get_connection_targets(
        self,
        *,
        connection_id: Optional[str] = None,
        connection: Optional[ConnRecord] = None,
    ):
        """Create a connection target from a `ConnRecord`.

        Args:
            connection_id: The connection ID to search for
            connection: The connection record itself, if already available
        """
        if connection_id is None and connection is None:
            raise ValueError("Must supply either connection_id or connection")

        if not connection_id:
            assert connection
            connection_id = connection.connection_id

        cache = self._profile.inject_or(BaseCache)
        cache_key = f"connection_target::{connection_id}"
        if cache:
            async with cache.acquire(cache_key) as entry:
                if entry.result:
                    self._logger.debug("Connection targets retrieved from cache")
                    targets = [ConnectionTarget.deserialize(row) for row in entry.result]
                else:
                    if not connection:
                        async with self._profile.session() as session:
                            connection = await ConnRecord.retrieve_by_id(
                                session, connection_id
                            )

                    targets = await self.fetch_connection_targets(connection)

                    if connection.state == ConnRecord.State.COMPLETED.rfc160:
                        # Only set cache if connection has reached completed state
                        # Otherwise, a replica that participated early in exchange
                        # may have bad data set in cache.
                        self._logger.debug("Caching connection targets")
                        await entry.set_result([row.serialize() for row in targets], 3600)
                    else:
                        self._logger.debug(
                            "Not caching connection targets for connection in "
                            f"state ({connection.state})"
                        )
        else:
            if not connection:
                async with self._profile.session() as session:
                    connection = await ConnRecord.retrieve_by_id(session, connection_id)

            targets = await self.fetch_connection_targets(connection)
        return targets

    async def clear_connection_targets_cache(self, connection_id: str):
        """Clear the connection targets cache for a given connection ID.

        Historically, connections have not been updatable after the protocol
        completes. However, with DID Rotation, we need to be able to update
        the connection targets and clear the cache of targets.
        """
        # TODO it would be better to include the DIDs of the connection in the
        # target cache key This solution only works when using whole cluster
        # caching or have only a single instance with local caching
        cache = self._profile.inject_or(BaseCache)
        if cache:
            cache_key = f"connection_target::{connection_id}"
            await cache.clear(cache_key)

    def diddoc_connection_targets(
        self,
        doc: Optional[Union[DIDDoc, dict]],
        sender_verkey: str,
        their_label: Optional[str] = None,
    ) -> Sequence[ConnectionTarget]:
        """Get a list of connection targets from a DID Document.

        Args:
            doc: The DID Document to create the target from
            sender_verkey: The verkey we are using
            their_label: The connection label they are using
        """
        if isinstance(doc, dict):
            doc = DIDDoc.deserialize(doc)
        if not doc:
            raise BaseConnectionManagerError("No DIDDoc provided for connection target")
        if not doc.did:
            raise BaseConnectionManagerError("DIDDoc has no DID")
        if not doc.service:
            raise BaseConnectionManagerError("No services defined by DIDDoc")

        targets = []
        for service in doc.service.values():
            if service.recip_keys:
                targets.append(
                    ConnectionTarget(
                        did=doc.did,
                        endpoint=service.endpoint,
                        label=their_label,
                        recipient_keys=[key.value for key in (service.recip_keys or ())],
                        routing_keys=[key.value for key in (service.routing_keys or ())],
                        sender_key=sender_verkey,
                    )
                )
        return targets

    async def fetch_did_document(self, did: str) -> Tuple[dict, StorageRecord]:
        """Retrieve a DID Document for a given DID.

        Args:
            did: The DID to search for
        """
        async with self._profile.session() as session:
            storage = session.inject(BaseStorage)
            record = await storage.find_record(self.RECORD_TYPE_DID_DOC, {"did": did})
        return json.loads(record.value), record

    async def find_connection(
        self,
        their_did: Optional[str],
        my_did: Optional[str] = None,
        parent_thread_id: Optional[str] = None,
        auto_complete=False,
    ) -> Optional[ConnRecord]:
        """Look up existing connection information for a sender verkey.

        Args:
            their_did: Their DID
            my_did: My DID
            parent_thread_id: Parent thread ID
            auto_complete: Should this connection automatically be promoted to active

        Returns:
            The located `ConnRecord`, if any

        """
        connection = None
        if their_did and their_did.startswith("did:peer:4"):
            # did:peer:4 always recorded as long
            long = their_did
            short = self.long_did_peer_to_short(their_did)
            try:
                async with self._profile.session() as session:
                    connection = await ConnRecord.retrieve_by_did_peer_4(
                        session, long, short, my_did
                    )
            except StorageNotFoundError:
                pass
        elif their_did:
            try:
                async with self._profile.session() as session:
                    connection = await ConnRecord.retrieve_by_did(
                        session, their_did, my_did
                    )
            except StorageNotFoundError:
                pass

        if (
            connection
            and ConnRecord.State.get(connection.state) is ConnRecord.State.RESPONSE
            and auto_complete
        ):
            connection.state = ConnRecord.State.COMPLETED.rfc160
            async with self._profile.session() as session:
                await connection.save(session, reason="Connection promoted to active")
                if session.settings.get("auto_disclose_features"):
                    discovery_mgr = V20DiscoveryMgr(self._profile)
                    await discovery_mgr.proactive_disclose_features(
                        connection_id=connection.connection_id
                    )

        if not connection and parent_thread_id:
            async with self._profile.session() as session:
                connection = await ConnRecord.retrieve_by_invitation_msg_id(
                    session,
                    parent_thread_id,
                    their_role=ConnRecord.Role.REQUESTER.rfc160,
                )

        return connection

    async def find_inbound_connection(
        self, receipt: MessageReceipt
    ) -> Optional[ConnRecord]:
        """Deserialize an incoming message and further populate the request context.

        Args:
            receipt: The message receipt

        Returns:
            The `ConnRecord` associated with the expanded message, if any

        """

        cache_key = None
        connection = None
        resolved = False

        if receipt.sender_verkey and receipt.recipient_verkey:
            cache_key = (
                f"connection_by_verkey::{receipt.sender_verkey}"
                f"::{receipt.recipient_verkey}"
            )
            cache = self._profile.inject_or(BaseCache)
            if cache:
                async with cache.acquire(cache_key) as entry:
                    if entry.result:
                        cached = entry.result
                        receipt.sender_did = cached["sender_did"]
                        receipt.recipient_did_public = cached["recipient_did_public"]
                        receipt.recipient_did = cached["recipient_did"]
                        async with self._profile.session() as session:
                            connection = await ConnRecord.retrieve_by_id(
                                session, cached["id"]
                            )
                    else:
                        connection = await self.resolve_inbound_connection(receipt)
                        if connection:
                            cache_val = {
                                "id": connection.connection_id,
                                "sender_did": receipt.sender_did,
                                "recipient_did": receipt.recipient_did,
                                "recipient_did_public": receipt.recipient_did_public,
                            }
                            await entry.set_result(cache_val, 3600)
                        resolved = True

        if not connection and not resolved:
            connection = await self.resolve_inbound_connection(receipt)
        return connection

    async def resolve_inbound_connection(
        self, receipt: MessageReceipt
    ) -> Optional[ConnRecord]:
        """Populate the receipt DID information and find the related `ConnRecord`.

        Args:
            receipt: The message receipt

        Returns:
            The `ConnRecord` associated with the expanded message, if any

        """

        receipt.sender_did = None
        if receipt.sender_verkey:
            try:
                receipt.sender_did = await self.find_did_for_key(receipt.sender_verkey)
            except StorageNotFoundError:
                pass

        if receipt.recipient_verkey:
            try:
                async with self._profile.session() as session:
                    wallet = session.inject(BaseWallet)
                    my_info = await wallet.get_local_did_for_verkey(
                        receipt.recipient_verkey
                    )
                receipt.recipient_did = my_info.did
                if "posted" in my_info.metadata and my_info.metadata["posted"] is True:
                    receipt.recipient_did_public = True
            except InjectionError:
                self._logger.warning(
                    "Cannot resolve recipient verkey, no wallet defined by context: %s",
                    receipt.recipient_verkey,
                )
            except WalletNotFoundError:
                self._logger.debug(
                    "No corresponding DID found for recipient verkey: %s",
                    receipt.recipient_verkey,
                )

        return await self.find_connection(
            receipt.sender_did, receipt.recipient_did, receipt.parent_thread_id, True
        )

    async def get_endpoints(self, conn_id: str) -> Tuple[Optional[str], Optional[str]]:
        """Get connection endpoints.

        Args:
            conn_id: connection identifier

        Returns:
            Their endpoint for this connection

        """
        async with self._profile.session() as session:
            connection = await ConnRecord.retrieve_by_id(session, conn_id)
            wallet = session.inject(BaseWallet)
            my_did_info = await wallet.get_local_did(connection.my_did)

        my_endpoint = my_did_info.metadata.get(
            "endpoint",
            self._profile.settings.get("default_endpoint"),
        )

        conn_targets = await self.get_connection_targets(
            connection_id=connection.connection_id,
            connection=connection,
        )
        return (my_endpoint, conn_targets[0].endpoint)

    async def create_static_connection(
        self,
        my_did: Optional[str] = None,
        my_seed: Optional[str] = None,
        their_did: Optional[str] = None,
        their_seed: Optional[str] = None,
        their_verkey: Optional[str] = None,
        their_endpoint: Optional[str] = None,
        their_label: Optional[str] = None,
        alias: Optional[str] = None,
        mediation_id: Optional[str] = None,
    ) -> Tuple[DIDInfo, DIDInfo, ConnRecord]:
        """Register a new static connection (for use by the test suite).

        This method is used to create a new static connection. It allows overriding
        various parameters such as DIDs, seeds, verkeys, endpoints, labels, and aliases.
        It returns the created connection record along with the associated DID
        information.

        Args:
            my_did (Optional[str]): Override the DID used in the connection.
            my_seed (Optional[str]): Provide a seed used to generate our DID and keys.
            their_did (Optional[str]): Provide the DID used by the other party.
            their_seed (Optional[str]): Provide a seed used to generate their DID and
                keys.
            their_verkey (Optional[str]): Provide the verkey used by the other party.
            their_endpoint (Optional[str]): Their URL endpoint for routing messages.
            their_label (Optional[str]): An alias for this connection record.
            alias (Optional[str]): An alias for this connection record.
            mediation_id (Optional[str]): The mediation ID for routing through a mediator.

        Returns:
            Tuple[DIDInfo, DIDInfo, ConnRecord]: A tuple containing the following:
                - my DIDInfo: The DID information for the local party.
                - their DIDInfo: The DID information for the other party.
                - new `ConnRecord` instance: The newly created connection record.

        Raises:
            BaseConnectionManagerError: If either a verkey or seed must be provided for
                the other party.

        """
        async with self._profile.session() as session:
            wallet = session.inject(BaseWallet)
            # seed and DID optional
            my_info = await wallet.create_local_did(SOV, ED25519, my_seed, my_did)

        # must provide their DID and verkey if the seed is not known
        if (not their_did or not their_verkey) and not their_seed:
            raise BaseConnectionManagerError(
                "Either a verkey or seed must be provided for the other party"
            )
        if not their_did:
            their_did = seed_to_did(their_seed)
        if not their_verkey:
            their_verkey_bin, _ = create_keypair(ED25519, their_seed.encode())
            their_verkey = bytes_to_b58(their_verkey_bin)
        their_info = DIDInfo(their_did, their_verkey, {}, method=SOV, key_type=ED25519)

        # Create connection record
        connection = ConnRecord(
            invitation_mode=ConnRecord.INVITATION_MODE_STATIC,
            my_did=my_info.did,
            their_did=their_info.did,
            their_label=their_label,
            state=ConnRecord.State.COMPLETED.rfc160,
            alias=alias,
            connection_protocol=CONN_PROTO,
        )
        async with self._profile.session() as session:
            await connection.save(session, reason="Created new static connection")
            if session.settings.get("auto_disclose_features"):
                discovery_mgr = V20DiscoveryMgr(self._profile)
                await discovery_mgr.proactive_disclose_features(
                    connection_id=connection.connection_id
                )

        # Routing
        mediation_record = await self._route_manager.mediation_record_if_id(
            self._profile, mediation_id, or_default=True
        )

        multitenant_mgr = self._profile.inject_or(BaseMultitenantManager)
        wallet_id = self._profile.settings.get("wallet.id")

        base_mediation_record = None
        if multitenant_mgr and wallet_id:
            base_mediation_record = await multitenant_mgr.get_default_mediator()

        await self._route_manager.route_static(
            self._profile, connection, mediation_record
        )

        # Synthesize their DID doc
        did_doc = await self.create_did_document(
            their_info,
            [their_endpoint or ""],
            mediation_records=list(
                filter(None, [base_mediation_record, mediation_record])
            ),
        )

        await self.store_did_document(did_doc)

        return my_info, their_info, connection
