"""
Class to provide some common utilities.

For Connection, DIDExchange and OutOfBand Manager.
"""

import logging
from typing import Optional, List, Sequence, Tuple, Text, Union

from multiformats import multibase, multicodec
from pydid import (
    BaseDIDDocument as ResolvedDocument,
    DIDDocument,
    DIDCommService,
    VerificationMethod,
)
import pydid
from pydid.verification_method import (
    Ed25519VerificationKey2018,
    JsonWebKey2020,
    Ed25519VerificationKey2020,
)
from pydid.did_url import DIDUrl

from ..config.logging import get_logger_inst
from ..core.error import BaseError
from ..core.profile import Profile
from ..did.did_key import DIDKey
from ..protocols.connections.v1_0.messages.connection_invitation import (
    ConnectionInvitation,
)
from ..protocols.coordinate_mediation.v1_0.models.mediation_record import (
    MediationRecord,
)
from ..protocols.coordinate_mediation.v1_0.route_manager import (
    RouteManager,
)
from ..resolver.base import ResolverError
from ..resolver.did_resolver import DIDResolver
from ..storage.base import BaseStorage
from ..storage.error import StorageNotFoundError
from ..storage.record import StorageRecord
from ..wallet.base import BaseWallet
from ..wallet.did_info import DIDInfo
from .models.conn_record import ConnRecord
from .models.connection_target import ConnectionTarget
from .models.diddoc import LegacyDIDDoc, PublicKey, PublicKeyType, Service, DIDDoc
from .models.diddoc.util import upgrade_legacy_did_doc_to_peer_did
from ..wallet.util import bytes_to_b58, b64_to_bytes


class BaseConnectionManagerError(BaseError):
    """BaseConnectionManager error."""


class BaseConnectionManager:
    """Class to provide utilities regarding connection_targets."""

    RECORD_TYPE_DID_DOC = "did_doc"
    RECORD_TYPE_DID_KEY = "did_key"

    def __init__(self, profile: Profile):
        """
        Initialize a BaseConnectionManager.

        Args:
            session: The profile session for this presentation
        """
        self._profile = profile
        self._route_manager = profile.inject(RouteManager)
        self._logger: logging.Logger = get_logger_inst(
            profile=self._profile,
            logger_name=__name__,
        )

    async def create_did_document(
        self,
        did_info: DIDInfo,
        inbound_connection_id: str = None,
        svc_endpoints: Sequence[str] = None,
        mediation_records: List[MediationRecord] = None,
    ) -> DIDDoc:
        """Create our DID doc for a given DID.

        Args:
            did_info: The DID information (DID and verkey) used in the connection
            inbound_connection_id: The ID of the inbound routing connection to use
            svc_endpoints: Custom endpoints for the DID Document
            mediation_record: The record for mediation that contains routing_keys and
                service endpoint

        Returns:
            The prepared `DIDDoc` instance

        """

        did_doc = DIDDoc(id=did_info.did)
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

        router_id = inbound_connection_id
        routing_keys = []
        router_idx = 1
        while router_id:
            # look up routing connection information
            async with self._profile.session() as session:
                router = await ConnRecord.retrieve_by_id(session, router_id)
            if ConnRecord.State.get(router.state) != ConnRecord.State.COMPLETED:
                raise BaseConnectionManagerError(
                    f"Router connection not completed: {router_id}"
                )
            routing_doc, _ = await self.fetch_did_document(router.their_did)
            if not routing_doc.service:
                raise BaseConnectionManagerError(
                    f"No services defined by routing DIDDoc: {router_id}"
                )
            for service in routing_doc.service:
                if not service.service_endpoint:
                    raise BaseConnectionManagerError(
                        "Routing DIDDoc service has no service endpoint"
                    )
                if not service.recipient_keys:
                    raise BaseConnectionManagerError(
                        "Routing DIDDoc service has no recipient key(s)"
                    )
                rk = PublicKey(
                    did_info.did,
                    f"routing-{router_idx}",
                    service.recipient_keys[0],
                    PublicKeyType.ED25519_SIG_2018,
                    did_controller,
                    True,
                )
                routing_keys.append(rk)
                svc_endpoints = [service.service_endpoint]
                break
            router_id = router.inbound_connection_id

        if mediation_records:
            for mediation_record in mediation_records:
                mediator_routing_keys = [
                    PublicKey(
                        did_info.did,
                        f"routing-{idx}",
                        key,
                        PublicKeyType.ED25519_SIG_2018,
                        did_controller,  # TODO: get correct controller did_info
                        True,  # TODO: should this be true?
                    )
                    for idx, key in enumerate(mediation_record.routing_keys)
                ]

                routing_keys = [*routing_keys, *mediator_routing_keys]
                svc_endpoints = [mediation_record.endpoint]

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

    async def store_did_document(self, did_doc: Union[DIDDocument,LegacyDIDDoc]):
        """Store a DID document.

        Args:
            did_doc: The `LegacyDIDDoc` instance to persist
        """
        assert did_doc.id

        try:
            stored_doc, record = await self.fetch_did_document(did_doc.id)
        except StorageNotFoundError:
            record = StorageRecord(
                self.RECORD_TYPE_DID_DOC,
                did_doc.to_json(),
                {"did": did_doc.id},
            )
            async with self._profile.session() as session:
                storage: BaseStorage = session.inject(BaseStorage)
                await storage.add_record(record)
        else:
            async with self._profile.session() as session:
                storage: BaseStorage = session.inject(BaseStorage)
                await storage.update_record(
                    record, did_doc.to_json(), {"did": did_doc.id}
                )
        await self.remove_keys_for_did(did_doc.id)
        if hasattr(did_doc, "pubkey"):
            for key in did_doc.pubkey.values():
                if key.controller == did_doc.id:
                    await self.add_key_for_did(did_doc.id, key.value)
        if hasattr(did_doc, "verification_method"):
            for vm in did_doc.verification_method or []:
                if vm.controller == did_doc.id:
                    if vm.public_key_base58:
                        await self.add_key_for_did(did_doc.id, vm.public_key_base58)
                    if vm.public_key_multibase:
                        await self.add_key_for_did(did_doc.id, bytes_to_b58(multibase.decode(vm.public_key_multibase)))
                    elif vm.material:
                        self._logger.error(
                            "VerificationMethod material exists, but no in base58, not saving key"
                        )

    async def add_key_for_did(self, did: str, key: str):
        """Store a verkey for lookup against a DID.

        Args:
            did: The DID to associate with this key
            key: The verkey to be added
        """
        record = StorageRecord(self.RECORD_TYPE_DID_KEY, key, {"did": did, "key": key})
        async with self._profile.session() as session:
            storage: BaseStorage = session.inject(BaseStorage)
            await storage.add_record(record)

    async def find_did_for_key(self, key: str) -> str:
        """Find the DID previously associated with a key.

        Args:
            key: The verkey to look up
        """
        async with self._profile.session() as session:
            storage: BaseStorage = session.inject(BaseStorage)
            record = await storage.find_record(self.RECORD_TYPE_DID_KEY, {"key": key})
        return record.tags["did"]

    async def remove_keys_for_did(self, did: str):
        """Remove all keys associated with a DID.

        Args:
            did: The DID for which to remove keys
        """
        async with self._profile.session() as session:
            storage: BaseStorage = session.inject(BaseStorage)
            await storage.delete_all_records(self.RECORD_TYPE_DID_KEY, {"did": did})

    async def resolve_invitation(
        self, did: str, service_accept: Optional[Sequence[Text]] = None
    ):
        """
        Resolve invitation with the DID Resolver.

        Args:
            did: Document ID to resolve
        """
        if not did.startswith("did:"):
            # DID is bare indy "nym"
            # prefix with did:sov: for backwards compatibility
            did = f"did:sov:{did}"

        resolver = self._profile.inject(DIDResolver)
        try:
            doc_dict: dict = await resolver.resolve(self._profile, did, service_accept)
            doc: ResolvedDocument = pydid.deserialize_document(doc_dict, strict=True)
        except ResolverError as error:
            raise BaseConnectionManagerError(
                "Failed to resolve public DID in invitation"
            ) from error

        if not doc.service:
            raise BaseConnectionManagerError(
                "Cannot connect via public DID that has no associated services"
            )

        didcomm_services = sorted(
            [service for service in doc.service if isinstance(service, DIDCommService)],
            key=lambda service: service.priority,
        )

        if not didcomm_services:
            raise BaseConnectionManagerError(
                "Cannot connect via public DID that has no associated DIDComm services"
            )

        first_didcomm_service, *_ = didcomm_services

        endpoint = first_didcomm_service.service_endpoint
        recipient_keys: List[VerificationMethod] = [
            await resolver.dereference(self._profile, url, document=doc)
            for url in first_didcomm_service.recipient_keys
        ]
        routing_keys: List[VerificationMethod] = [
            await resolver.dereference(self._profile, url, document=doc)
            for url in first_didcomm_service.routing_keys
        ]

        return (
            endpoint,
            [
                self._extract_key_material_in_base58_format(key)
                for key in recipient_keys
            ],
            [self._extract_key_material_in_base58_format(key) for key in routing_keys],
        )

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
        else:
            raise BaseConnectionManagerError(
                f"Key type {type(method).__name__} is not supported"
            )

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
            return None
        results = None

        if (
            ConnRecord.State.get(connection.state)
            in (ConnRecord.State.INVITATION, ConnRecord.State.REQUEST)
            and ConnRecord.Role.get(connection.their_role) is ConnRecord.Role.RESPONDER
        ):
            if (
                connection.invitation_msg_id
                or connection.invitation_key
                or not connection.their_did
            ):
                async with self._profile.session() as session:
                    invitation = await connection.retrieve_invitation(session)
                if isinstance(
                    invitation, ConnectionInvitation
                ):  # conn protocol invitation
                    if invitation.did:
                        did = invitation.did
                        (
                            endpoint,
                            recipient_keys,
                            routing_keys,
                        ) = await self.resolve_invitation(did)

                    else:
                        endpoint = invitation.endpoint
                        recipient_keys = invitation.recipient_keys
                        routing_keys = invitation.routing_keys
                else:  # out-of-band invitation
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
                            DIDKey.from_did(k).public_key_b58
                            for k in oob_service_item.recipient_keys
                        ]
                        routing_keys = [
                            DIDKey.from_did(k).public_key_b58
                            for k in oob_service_item.routing_keys
                        ]
            else:
                if connection.their_did:
                    invitation = None
                    did = connection.their_did
                    (
                        endpoint,
                        recipient_keys,
                        routing_keys,
                    ) = await self.resolve_invitation(did)

            async with self._profile.session() as session:
                wallet = session.inject(BaseWallet)
                my_info = await wallet.get_local_did(connection.my_did)

            results = [
                ConnectionTarget(
                    did=connection.their_did,
                    endpoint=endpoint,
                    label=invitation.label if invitation else None,
                    recipient_keys=recipient_keys,
                    routing_keys=routing_keys,
                    sender_key=my_info.verkey,
                )
            ]
        else:
            did_doc = None
            if not connection.their_did:
                self._logger.debug("No target DID associated with connection")
                return None
            try:
                did_doc, _ = await self.fetch_did_document(connection.their_did)

            except StorageNotFoundError:
                self._logger.warning(
                    "did_document not found, checking with did:sov: prefix to manage legacy behaviour"
                )
                did_doc, _ = await self.fetch_did_document(
                    "did:sov:" + connection.their_did
                )

            finally:
                if not did_doc:
                    raise StorageNotFoundError(
                        f"did_document not found with did {connection.their_did}"
                    )

            async with self._profile.session() as session:
                wallet = session.inject(BaseWallet)
                my_info = await wallet.get_local_did(connection.my_did)

            results = self.diddoc_connection_targets(
                did_doc, my_info.verkey, connection.their_label
            )

        return results

    def resolve_verkey_references(
        self, did_doc: DIDDocument, values_or_refs=List[str]
    ) -> List[str]:
        """resolve verkey_references in DIDDocument and return a list of b58 encoded verkeys"""
        result = []
        resource = None
        for vor in values_or_refs:
            if DIDUrl.is_valid(vor):
                resource = did_doc.dereference(vor)
            else:
                # add if not a reference
                result.append(vor)

            if issubclass(resource.__class__, VerificationMethod):
                # insert material of verificationmethod
                vk = multibase.decode(resource.material)
        
                if len(vk) == 32:  # No multicodec prefix
                    vk = bytes_to_b58(vk)
                else:
                    codec, key = multicodec.unwrap(vk)
                    if codec == multicodec.multicodec("ed25519-pub"):
                        vk = bytes_to_b58(key)
                result.append(vk)
            else:
                # if the reference is to another type of object, log an error
                self._logger.error(
                    f"do not know the desired value to object of type {resource.__class__}."
                )
        return result

    def diddoc_connection_targets(
        self, doc: DIDDocument, sender_verkey: str, their_label: str = None
    ) -> Sequence[ConnectionTarget]:
        """Get a list of connection targets from a DID Document.

        Args:
            doc: The DID Document to create the target from
            sender_verkey: The verkey we are using
            their_label: The connection label they are using
        """
        if not doc:
            raise BaseConnectionManagerError(
                "No LegacyDIDDoc provided for connection target"
            )
        if not doc.id:
            raise BaseConnectionManagerError("LegacyDIDDoc has no DID")
        if not doc.service:
            raise BaseConnectionManagerError("No services defined in DIDDocument")

        targets = []
        for service in doc.service:
            recipient_verkeys = self.resolve_verkey_references(
                doc, service.recipient_keys
            )
            targets.append(
                ConnectionTarget(
                    did=doc.id,
                    endpoint=service.service_endpoint,
                    label=their_label,
                    recipient_keys=recipient_verkeys,
                    routing_keys=[key.value for key in (service.dict().get("routing_keys",[]))],
                    sender_key=sender_verkey,
                )
            )
        return targets

    async def fetch_did_document(self, did: str) -> Tuple[DIDDocument, StorageRecord]:
        """Retrieve a DID Document for a given DID.

        Args:
            did: The DID to search for
        """
        async with self._profile.session() as session:
            storage = session.inject(BaseStorage)
            record = await storage.find_record(self.RECORD_TYPE_DID_DOC, {"did": did})
            # JSload into LegacyDIDDoc, converting old DIDDoc classes into DIDDocument compliant objects
        try:
            return DIDDocument.from_json(record.value), record
        except Exception as e: 
            self._logger.warning("EXCEPTION LOADING DID_DOC")
            self._logger.warning(str(e))
            self._logger.warning("Attemping conversion to peer_did_2 and document")
            did,doc = upgrade_legacy_did_doc_to_peer_did(record.value)
            self._logger.warning("conversion complete, updating record in wallet with complaint record")
            await self.store_did_document(doc)
            self._logger.warning("Update successful.")
            return doc, record

