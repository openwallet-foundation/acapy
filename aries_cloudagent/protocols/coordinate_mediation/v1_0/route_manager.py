"""Route manager.

Set up routing for newly formed connections.
"""


from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

from aries_cloudagent.protocols.routing.v1_0.models.route_record import RouteRecord
from aries_cloudagent.storage.error import StorageNotFoundError

from ....connections.models.conn_record import ConnRecord
from ....core.profile import Profile
from ....messaging.responder import BaseResponder
from ....wallet.base import BaseWallet
from ....wallet.did_info import DIDInfo
from ....wallet.did_method import DIDMethod
from ....wallet.key_type import KeyType
from .manager import MediationManager
from .models.mediation_record import MediationRecord


class RouteManagerError(Exception):
    """Raised on error from route manager."""


class RouteManager(ABC):
    """Base Route Manager."""

    def __init__(self, profile: Profile):
        self.profile = profile

    async def get_or_create_my_did(self, conn_record: ConnRecord) -> DIDInfo:
        if not conn_record.my_did:
            async with self.profile.session() as session:
                wallet = session.inject(BaseWallet)
                # Create new DID for connection
                my_info = await wallet.create_local_did(DIDMethod.SOV, KeyType.ED25519)
                conn_record.my_did = my_info.did
                await conn_record.save(session, reason="Connection my did created")
        else:
            async with self.profile.session() as session:
                wallet = session.inject(BaseWallet)
                my_info = await wallet.get_local_did(conn_record.my_did)

        return my_info

    def _validate_mediation_state(self, mediation_record: MediationRecord):
        if mediation_record.state != MediationRecord.STATE_GRANTED:
            raise RouteManagerError(
                "Mediation is not granted for mediation identified by "
                f"{mediation_record.mediation_id}"
            )

    async def mediation_record_for_connection(
        self,
        conn_record: ConnRecord,
        mediation_id: Optional[str] = None,
        or_default: bool = False,
    ):
        """Validate mediation and return record.

        If mediation_id is not None,
        validate mediation record state and return record
        else, return None
        """
        mediation_record = None
        async with self.profile.session() as session:
            try:
                mediation_record = await MediationRecord.retrieve_by_connection_id(
                    session, conn_record.connection_id
                )
            except StorageNotFoundError:
                pass

        if mediation_record:
            self._validate_mediation_state(mediation_record)
            return mediation_record

        return await self.mediation_record_if_id(mediation_id, or_default)

    async def mediation_record_if_id(
        self, mediation_id: Optional[str] = None, or_default: bool = False
    ):
        """Validate mediation and return record.

        If mediation_id is not None,
        validate mediation record state and return record
        else, return None
        """
        mediation_record = None
        if mediation_id:
            async with self.profile.session() as session:
                mediation_record = await MediationRecord.retrieve_by_id(
                    session, mediation_id
                )
        elif or_default:
            mediation_record = await MediationManager(
                self.profile
            ).get_default_mediator()

        if mediation_record:
            self._validate_mediation_state(mediation_record)
        return mediation_record

    @abstractmethod
    async def _route_for_key(
        self,
        recipient_key: str,
        mediation_record: Optional[MediationRecord] = None,
        *,
        skip_if_exists: bool = False,
        replace_key: Optional[str] = None,
    ):
        """Route a key."""

    async def route_connection_as_invitee(
        self,
        conn_record: ConnRecord,
        mediation_record: Optional[MediationRecord] = None,
    ):
        """Set up routing for a new connection when we are the invitee."""
        my_info = await self.get_or_create_my_did(conn_record)
        return await self._route_for_key(
            my_info.verkey, mediation_record, skip_if_exists=True
        )

    async def route_connection_as_inviter(
        self,
        conn_record: ConnRecord,
        mediation_record: Optional[MediationRecord] = None,
    ):
        """Set up routing for a new connection when we are the inviter."""
        my_info = await self.get_or_create_my_did(conn_record)
        return await self._route_for_key(
            my_info.verkey,
            mediation_record,
            replace_key=conn_record.invitation_key,
            skip_if_exists=True,
        )

    async def route_connection(
        self,
        conn_record: ConnRecord,
        mediation_record: Optional[MediationRecord] = None,
    ):
        if conn_record.rfc23_state == ConnRecord.State.INVITATION.rfc23strict(
            ConnRecord.Role.REQUESTER
        ):
            return await self.route_connection_as_invitee(conn_record, mediation_record)

        if conn_record.rfc23_state == ConnRecord.State.REQUEST.rfc23strict(
            ConnRecord.Role.RESPONDER
        ):
            return await self.route_connection_as_inviter(conn_record, mediation_record)

        return None

    async def route_invitation(
        self,
        conn_record: ConnRecord,
        mediation_record: Optional[MediationRecord] = None,
    ):
        """Set up routing for receiving a response to an invitation."""
        if mediation_record:
            # Save that this invitation was created with mediation
            async with self.profile.session() as session:
                await conn_record.metadata_set(
                    session,
                    MediationManager.METADATA_KEY,
                    {MediationManager.METADATA_ID: mediation_record.mediation_id},
                )

        if conn_record.invitation_key:
            return await self._route_for_key(
                conn_record.invitation_key, mediation_record, skip_if_exists=True
            )

        raise ValueError("Expected connection to have invitation_key")

    async def route_public_did(self, verkey: str):
        """Establish routing for a public DID."""
        return await self._route_for_key(verkey, skip_if_exists=True)

    async def route_static(
        self,
        conn_record: ConnRecord,
        mediation_record: Optional[MediationRecord] = None,
    ):
        my_info = await self.get_or_create_my_did(conn_record)
        return await self._route_for_key(
            my_info.verkey, mediation_record, skip_if_exists=True
        )

    @abstractmethod
    async def routing_info(
        self,
        my_endpoint: str,
        mediation_record: Optional[MediationRecord] = None,
    ) -> Tuple[List[str], str]:
        """Retrieve routing keys."""


class CoordinateMediationV1RouteManager(RouteManager):
    """Manage routes using Coordinate Mediation protocol."""

    async def _route_for_key(
        self,
        recipient_key: str,
        mediation_record: Optional[MediationRecord] = None,
        *,
        skip_if_exists: bool = False,
        replace_key: Optional[str] = None,
    ):
        if not mediation_record:
            return None

        if skip_if_exists:
            try:
                async with self.profile.session() as session:
                    await RouteRecord.retrieve_by_recipient_key(session, recipient_key)

                return None
            except StorageNotFoundError:
                pass

        # Keylist update is idempotent, skip_if_exists ignored
        mediation_mgr = MediationManager(self.profile)
        keylist_update = await mediation_mgr.add_key(recipient_key)
        if replace_key:
            keylist_update = await mediation_mgr.remove_key(replace_key)

        responder = self.profile.inject(BaseResponder)
        await responder.send(
            keylist_update, connection_id=mediation_record.connection_id
        )
        return keylist_update

    async def routing_info(
        self, my_endpoint: str, mediation_record: Optional[MediationRecord] = None
    ) -> Tuple[List[str], str]:
        if mediation_record:
            return mediation_record.routing_keys, mediation_record.endpoint

        return [], my_endpoint
