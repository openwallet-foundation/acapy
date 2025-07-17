"""Route manager.

Set up routing for newly formed connections.
"""

import logging
from abc import ABC, abstractmethod
from typing import List, NamedTuple, Optional

from ....connections.models.conn_record import ConnRecord
from ....core.profile import Profile
from ....messaging.responder import BaseResponder
from ....storage.error import StorageNotFoundError
from ....wallet.base import BaseWallet
from ....wallet.did_info import DIDInfo
from ....wallet.did_method import SOV
from ....wallet.key_type import ED25519
from ...routing.v1_0.models.route_record import RouteRecord
from .manager import MediationManager
from .messages.keylist_update import KeylistUpdate
from .models.mediation_record import MediationRecord
from .normalization import normalize_from_did_key, normalize_to_did_key

LOGGER = logging.getLogger(__name__)


class RouteManagerError(Exception):
    """Raised on error from route manager."""


class RoutingInfo(NamedTuple):
    """Routing info tuple containing routing keys and endpoint."""

    routing_keys: Optional[List[str]]
    endpoint: Optional[str]

    @classmethod
    def empty(cls):
        """Empty routing info."""
        return cls(routing_keys=None, endpoint=None)


class RouteManager(ABC):
    """Base Route Manager."""

    async def get_or_create_my_did(
        self, profile: Profile, conn_record: ConnRecord
    ) -> DIDInfo:
        """Create or retrieve DID info for a connection."""
        if not conn_record.my_did:
            async with profile.session() as session:
                wallet = session.inject(BaseWallet)

                LOGGER.debug(
                    "Creating new DID for connection %s", conn_record.connection_id
                )
                my_info = await wallet.create_local_did(SOV, ED25519)
                conn_record.my_did = my_info.did
                await conn_record.save(session, reason="Connection my did created")
        else:
            async with profile.session() as session:
                wallet = session.inject(BaseWallet)
                LOGGER.debug(
                    "Getting DID info for connection %s", conn_record.connection_id
                )
                my_info = await wallet.get_local_did(conn_record.my_did)

        return my_info

    def _validate_mediation_state(self, mediation_record: MediationRecord):
        """Perform mediation state validation."""
        if mediation_record.state != MediationRecord.STATE_GRANTED:
            LOGGER.error(
                "Mediation is not granted for mediation identified by %s",
                mediation_record.mediation_id,
            )
            raise RouteManagerError(
                "Mediation is not granted for mediation identified by "
                f"{mediation_record.mediation_id}"
            )

    async def mediation_records_for_connection(
        self,
        profile: Profile,
        conn_record: ConnRecord,
        mediation_id: Optional[str] = None,
        or_default: bool = False,
    ) -> List[MediationRecord]:
        """Return relevant mediator for connection."""
        # TODO Support multiple mediators?
        if conn_record.connection_id:
            async with profile.session() as session:
                mediation_metadata = await conn_record.metadata_get(
                    session, MediationManager.METADATA_KEY, {}
                )
                mediation_id = (
                    mediation_metadata.get(MediationManager.METADATA_ID) or mediation_id
                )

        mediation_record = await self.mediation_record_if_id(
            profile, mediation_id, or_default
        )
        if mediation_record:
            await self.save_mediator_for_connection(
                profile, conn_record, mediation_record
            )
        return [mediation_record] if mediation_record else []

    async def mediation_record_if_id(
        self,
        profile: Profile,
        mediation_id: Optional[str] = None,
        or_default: bool = False,
    ):
        """Validate mediation and return record.

        If mediation_id is not None,
        validate mediation record state and return record
        else, return None
        """
        mediation_record = None
        if mediation_id:
            async with profile.session() as session:
                mediation_record = await MediationRecord.retrieve_by_id(
                    session, mediation_id
                )
        elif or_default:
            mediation_record = await MediationManager(profile).get_default_mediator()

        if mediation_record:
            self._validate_mediation_state(mediation_record)
        return mediation_record

    @abstractmethod
    async def _route_for_key(
        self,
        profile: Profile,
        recipient_key: str,
        mediation_record: Optional[MediationRecord] = None,
        *,
        skip_if_exists: bool = False,
        replace_key: Optional[str] = None,
    ) -> Optional[KeylistUpdate]:
        """Route a key."""

    async def route_connection_as_invitee(
        self,
        profile: Profile,
        conn_record: ConnRecord,
        mediation_records: List[MediationRecord],
    ) -> Optional[KeylistUpdate]:
        """Set up routing for a new connection when we are the invitee."""
        LOGGER.debug("Routing connection as invitee")
        my_info = await self.get_or_create_my_did(profile, conn_record)
        # Only most destward mediator receives keylist updates
        mediation_record = mediation_records[0] if mediation_records else None
        return await self._route_for_key(
            profile, my_info.verkey, mediation_record, skip_if_exists=True
        )

    async def route_connection_as_inviter(
        self,
        profile: Profile,
        conn_record: ConnRecord,
        mediation_records: List[MediationRecord],
    ) -> Optional[KeylistUpdate]:
        """Set up routing for a new connection when we are the inviter."""
        LOGGER.debug("Routing connection as inviter")
        my_info = await self.get_or_create_my_did(profile, conn_record)

        replace_key = conn_record.invitation_key
        async with profile.session() as session:
            wallet = session.inject(BaseWallet)
            public_did = await wallet.get_public_did()

        # Do not replace key, if it is public
        if public_did and public_did.verkey == conn_record.invitation_key:
            replace_key = None

        # Only most destward mediator receives keylist updates
        mediation_record = mediation_records[0] if mediation_records else None

        return await self._route_for_key(
            profile,
            my_info.verkey,
            mediation_record,
            replace_key=replace_key,
            skip_if_exists=True,
        )

    async def route_connection(
        self,
        profile: Profile,
        conn_record: ConnRecord,
        mediation_records: List[MediationRecord],
    ) -> Optional[KeylistUpdate]:
        """Set up routing for a connection.

        This method will evaluate connection state and call the appropriate methods.
        """
        if conn_record.rfc23_state == ConnRecord.State.INVITATION.rfc23strict(
            ConnRecord.Role.RESPONDER
        ):
            return await self.route_connection_as_invitee(
                profile, conn_record, mediation_records
            )

        if conn_record.rfc23_state == ConnRecord.State.REQUEST.rfc23strict(
            ConnRecord.Role.REQUESTER
        ):
            return await self.route_connection_as_inviter(
                profile, conn_record, mediation_records
            )

        return None

    async def route_invitation(
        self,
        profile: Profile,
        conn_record: ConnRecord,
        mediation_record: Optional[MediationRecord] = None,
    ) -> Optional[KeylistUpdate]:
        """Set up routing for receiving a response to an invitation."""
        await self.save_mediator_for_connection(profile, conn_record, mediation_record)

        if conn_record.invitation_key:
            LOGGER.debug("Routing invitation key %s", conn_record.invitation_key)
            return await self._route_for_key(
                profile,
                conn_record.invitation_key,
                mediation_record,
                skip_if_exists=True,
            )

        raise ValueError("Expected connection to have invitation_key")

    async def route_verkey(
        self,
        profile: Profile,
        verkey: str,
        mediation_record: Optional[MediationRecord] = None,
    ):
        """Establish routing for a public DID."""
        LOGGER.debug(
            "Routing verkey %s%s", verkey, " with mediation" if mediation_record else ""
        )
        return await self._route_for_key(
            profile, verkey, mediation_record, skip_if_exists=True
        )

    async def route_public_did(self, profile: Profile, verkey: str):
        """Establish routing for a public DID.

        [DEPRECATED] Establish routing for a public DID. Use route_verkey() instead.
        """
        return await self._route_for_key(profile, verkey, skip_if_exists=True)

    async def route_static(
        self,
        profile: Profile,
        conn_record: ConnRecord,
        mediation_record: Optional[MediationRecord] = None,
    ) -> Optional[KeylistUpdate]:
        """Establish routing for a static connection."""
        LOGGER.debug("Routing static connection")
        my_info = await self.get_or_create_my_did(profile, conn_record)
        return await self._route_for_key(
            profile, my_info.verkey, mediation_record, skip_if_exists=True
        )

    async def save_mediator_for_connection(
        self,
        profile: Profile,
        conn_record: ConnRecord,
        mediation_record: Optional[MediationRecord] = None,
        mediation_id: Optional[str] = None,
    ):
        """Save mediator info to connection metadata."""
        async with profile.session() as session:
            if mediation_id:
                mediation_record = await MediationRecord.retrieve_by_id(
                    session, mediation_id
                )

            if mediation_record:
                await conn_record.metadata_set(
                    session,
                    MediationManager.METADATA_KEY,
                    {MediationManager.METADATA_ID: mediation_record.mediation_id},
                )

    @abstractmethod
    async def routing_info(
        self,
        profile: Profile,
        mediation_record: Optional[MediationRecord] = None,
    ) -> RoutingInfo:
        """Retrieve routing keys."""

    async def connection_from_recipient_key(
        self, profile: Profile, recipient_key: str
    ) -> ConnRecord:
        """Retrieve connection for a recipient_key.

        The recipient key is expected to be a local key owned by this agent.
        """
        async with profile.session() as session:
            wallet = session.inject(BaseWallet)
            try:
                conn = await ConnRecord.retrieve_by_tag_filter(
                    session, {"invitation_key": normalize_from_did_key(recipient_key)}
                )
            except StorageNotFoundError:
                did_info = await wallet.get_local_did_for_verkey(
                    normalize_from_did_key(recipient_key)
                )
                conn = await ConnRecord.retrieve_by_did(session, my_did=did_info.did)

            return conn


class CoordinateMediationV1RouteManager(RouteManager):
    """Manage routes using Coordinate Mediation protocol."""

    async def _route_for_key(
        self,
        profile: Profile,
        recipient_key: str,
        mediation_record: Optional[MediationRecord] = None,
        *,
        skip_if_exists: bool = False,
        replace_key: Optional[str] = None,
    ) -> Optional[KeylistUpdate]:
        LOGGER.debug("Routing for key %s using coordinate mediation", recipient_key)
        if not mediation_record:
            return None

        if skip_if_exists:
            try:
                async with profile.session() as session:
                    await RouteRecord.retrieve_by_recipient_key(session, recipient_key)

                return None
            except StorageNotFoundError:
                pass

        # Keylist update is idempotent, skip_if_exists ignored
        mediation_mgr = MediationManager(profile)
        keylist_update = await mediation_mgr.add_key(recipient_key)
        if replace_key:
            keylist_update = await mediation_mgr.remove_key(replace_key, keylist_update)

        responder = profile.inject(BaseResponder)
        await responder.send(keylist_update, connection_id=mediation_record.connection_id)
        return keylist_update

    async def routing_info(
        self,
        profile: Profile,
        mediation_record: Optional[MediationRecord] = None,
    ) -> RoutingInfo:
        """Return routing info for mediator."""
        if mediation_record:
            return RoutingInfo(
                routing_keys=[
                    normalize_to_did_key(key).key_id
                    for key in mediation_record.routing_keys
                ],
                endpoint=mediation_record.endpoint,
            )

        return RoutingInfo.empty()
