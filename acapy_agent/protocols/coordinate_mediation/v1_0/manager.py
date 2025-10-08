"""Manager for Mediation coordination."""

import json
import logging
from typing import Dict, Optional, Sequence, Tuple

from ....core.error import BaseError
from ....core.profile import Profile, ProfileSession
from ....storage.base import BaseStorage
from ....storage.error import StorageNotFoundError
from ....storage.record import StorageRecord
from ....wallet.base import BaseWallet
from ....wallet.did_info import DIDInfo
from ....wallet.did_method import SOV
from ....wallet.key_type import ED25519
from ...routing.v1_0.manager import RoutingManager, RoutingManagerError
from ...routing.v1_0.models.route_record import RouteRecord
from .messages.inner.keylist_key import KeylistKey
from .messages.inner.keylist_query_paginate import KeylistQueryPaginate
from .messages.inner.keylist_update_rule import KeylistUpdateRule
from .messages.inner.keylist_updated import KeylistUpdated
from .messages.keylist import Keylist
from .messages.keylist_query import KeylistQuery
from .messages.keylist_update import KeylistUpdate
from .messages.keylist_update_response import KeylistUpdateResponse
from .messages.mediate_deny import MediationDeny
from .messages.mediate_grant import MediationGrant
from .messages.mediate_request import MediationRequest
from .models.mediation_record import MediationRecord
from .normalization import normalize_from_did_key, normalize_to_did_key

LOGGER = logging.getLogger(__name__)


class MediationManagerError(BaseError):
    """Generic Mediation error."""


class MediationAlreadyExists(MediationManagerError):
    """Raised on mediation record already exists for given connection."""


class MediationNotGrantedError(MediationManagerError):
    """Raised when mediation state should be granted and is not."""


class MediationManager:
    """Class for handling Mediation.

    MediationManager creates or retrieves a routing DID as a means to hand out
    a consistent routing key to mediation clients.
    """

    ROUTING_DID_RECORD_TYPE = "routing_did"
    DEFAULT_MEDIATOR_RECORD_TYPE = "default_mediator"
    SEND_REQ_AFTER_CONNECTION = "send_mediation_request_on_connection"
    SET_TO_DEFAULT_ON_GRANTED = "set_to_default_on_granted"
    METADATA_KEY = "mediation"
    METADATA_ID = "id"
    KEYLIST_UPDATED_EVENT = "acapy::keylist::updated"

    def __init__(self, profile: Profile):
        """Initialize Mediation Manager.

        Args:
            profile: The Profile instance for this manager

        """
        self._profile = profile
        if not profile:
            raise MediationManagerError("Missing profile")

    # Role: Server {{{

    async def _retrieve_routing_did(self, session: ProfileSession) -> Optional[DIDInfo]:
        """Retrieve routing DID from the store.

        Args:
            session: An active profile session

        Returns:
            Optional[DIDInfo]: retrieved DID info or None if not found

        """
        storage = session.inject(BaseStorage)
        wallet = session.inject(BaseWallet)
        try:
            record = await storage.get_record(
                record_type=self.ROUTING_DID_RECORD_TYPE,
                record_id=self.ROUTING_DID_RECORD_TYPE,
            )
            info = json.loads(record.value)
            info.update(record.tags)
            did_info = await wallet.get_local_did(record.tags["did"])

            return did_info
        except StorageNotFoundError:
            return None

    async def _create_routing_did(self, session: ProfileSession) -> DIDInfo:
        """Create routing DID.

        Args:
            session: An active profile session

        Returns:
            DIDInfo: created routing DID info

        """
        wallet = session.inject(BaseWallet)
        storage = session.inject(BaseStorage)
        info = await wallet.create_local_did(
            method=SOV,
            key_type=ED25519,
            metadata={"type": "routing_did"},
        )
        record = StorageRecord(
            type=self.ROUTING_DID_RECORD_TYPE,
            value=json.dumps({"verkey": info.verkey, "metadata": info.metadata}),
            tags={"did": info.did},
            id=self.ROUTING_DID_RECORD_TYPE,
        )
        await storage.add_record(record)
        return info

    async def receive_request(
        self, connection_id: str, request: MediationRequest
    ) -> MediationRecord:
        """Create a new mediation record to track this request.

        Args:
            connection_id (str): connection ID of mediator
            request (MediationRequest): request message

        Returns:
            MediationRecord: record created during receipt of request.

        """
        async with self._profile.session() as session:
            if await MediationRecord.exists_for_connection_id(session, connection_id):
                raise MediationAlreadyExists(
                    "MediationRecord already exists for connection"
                )

            record = MediationRecord(
                connection_id=connection_id,
            )
            await record.save(session, reason="New mediation request received")
        return record

    async def grant_request(
        self, mediation_id: str
    ) -> Tuple[MediationRecord, MediationGrant]:
        """Grant a mediation request and prepare grant message.

        Args:
            mediation_id: mediation record ID to grant

        Returns:
            (MediationRecord, MediationGrant): updated mediation record and message to
            return to grantee

        """
        async with self._profile.session() as session:
            mediation_record = await MediationRecord.retrieve_by_id(session, mediation_id)
            if mediation_record.role != MediationRecord.ROLE_SERVER:
                raise MediationManagerError(
                    f"role({mediation_record.role}) is not {MediationRecord.ROLE_SERVER}"
                )

            routing_did = await self._retrieve_routing_did(session)
            if not routing_did:
                routing_did = await self._create_routing_did(session)

            mediation_record.state = MediationRecord.STATE_GRANTED

            await mediation_record.save(session, reason="Mediation request granted")
            grant = MediationGrant(
                endpoint=session.settings.get("default_endpoint"),
                routing_keys=[normalize_to_did_key(routing_did.verkey).key_id],
            )
        return mediation_record, grant

    async def deny_request(
        self,
        mediation_id: str,
    ) -> Tuple[MediationRecord, MediationDeny]:
        """Deny a mediation request and prepare a deny message.

        Args:
            mediation_id: mediation record ID to deny
        Returns:
            MediationDeny: message to return to denied client.

        """
        async with self._profile.session() as session:
            mediation_record = await MediationRecord.retrieve_by_id(session, mediation_id)
            if mediation_record.role != MediationRecord.ROLE_SERVER:
                raise MediationManagerError(
                    f"role({mediation_record.role}) is not {MediationRecord.ROLE_SERVER}"
                )

            mediation_record.state = MediationRecord.STATE_DENIED
            await mediation_record.save(session, reason="Mediation request denied")

        deny = MediationDeny()
        return mediation_record, deny

    async def _handle_keylist_update_add(
        self,
        existing_keys: Dict[str, RouteRecord],
        client_connection_id: str,
        recipient_key: str,
    ):
        """Handle creation of as directed by a keylist update."""
        route_mgr = RoutingManager(self._profile)
        if recipient_key in existing_keys:
            return KeylistUpdated.RESULT_NO_CHANGE
        try:
            await route_mgr.create_route_record(
                client_connection_id=client_connection_id,
                recipient_key=recipient_key,
            )
        except RoutingManagerError:
            LOGGER.exception("Error adding route record")
            return KeylistUpdated.RESULT_SERVER_ERROR
        return KeylistUpdated.RESULT_SUCCESS

    async def _handle_keylist_update_remove(
        self,
        existing_keys: Dict[str, RouteRecord],
        recipient_key: str,
    ):
        """Handle deletion of as directed by a keylist update."""
        route_mgr = RoutingManager(self._profile)
        if recipient_key not in existing_keys:
            return KeylistUpdated.RESULT_NO_CHANGE
        try:
            await route_mgr.delete_route_record(existing_keys[recipient_key])
        except RoutingManagerError:
            LOGGER.exception("Error deleting route record")
            return KeylistUpdated.RESULT_SERVER_ERROR
        return KeylistUpdated.RESULT_SUCCESS

    async def update_keylist(
        self, record: MediationRecord, updates: Sequence[KeylistUpdateRule]
    ) -> KeylistUpdateResponse:
        """Update routes defined in keylist update rules.

        Args:
            record (MediationRecord): record associated with client updating keylist
            updates (Sequence[KeylistUpdateRule]): updates to apply

        Returns:
            KeylistUpdateResponse: message to return to client

        """
        if record.state != MediationRecord.STATE_GRANTED:
            raise MediationNotGrantedError(
                "Mediation has not been granted for this connection."
            )

        route_mgr = RoutingManager(self._profile)
        routes = await route_mgr.get_routes(record.connection_id)
        existing_keys = {normalize_from_did_key(r.recipient_key): r for r in routes}

        updated = []
        for update in updates:
            normalized_key = normalize_from_did_key(update.recipient_key)
            result = KeylistUpdated(
                recipient_key=update.recipient_key,
                action=update.action,
            )

            # Assign result
            if not update.recipient_key:
                result.result = KeylistUpdated.RESULT_CLIENT_ERROR
            elif update.action == KeylistUpdateRule.RULE_ADD:
                result.result = await self._handle_keylist_update_add(
                    existing_keys, record.connection_id, normalized_key
                )
            elif update.action == KeylistUpdateRule.RULE_REMOVE:
                result.result = await self._handle_keylist_update_remove(
                    existing_keys, normalized_key
                )
            else:
                result.result = KeylistUpdated.RESULT_CLIENT_ERROR

            updated.append(result)

        return KeylistUpdateResponse(updated=updated)

    async def get_keylist(self, record: MediationRecord) -> Sequence[RouteRecord]:
        """Retrieve keylist for mediation client.

        Args:
            record (MediationRecord): record associated with client keylist

        Returns:
            Sequence[RouteRecord]: sequence of routes (the keylist)

        """
        if record.state != MediationRecord.STATE_GRANTED:
            raise MediationNotGrantedError(
                "Mediation has not been granted for this connection."
            )
        route_mgr = RoutingManager(self._profile)
        return await route_mgr.get_routes(record.connection_id)

    async def create_keylist_query_response(
        self, keylist: Sequence[RouteRecord]
    ) -> Keylist:
        """Prepare a keylist message from keylist.

        Args:
            keylist (Sequence[RouteRecord]): keylist to format into message

        Returns:
            Keylist: message to return to client

        """
        keys = [KeylistKey(recipient_key=key.recipient_key) for key in keylist]
        return Keylist(keys=keys, pagination=None)

    # }}}

    # Role: Client {{{

    async def _get_default_record(
        self, session: ProfileSession
    ) -> Optional[StorageRecord]:
        """Retrieve the default mediator raw record for use in updating or deleting.

        Args:
            session: An active profile session

        Returns:
            Optional[StorageRecord]: Record if present

        """
        storage = session.inject(BaseStorage)
        try:
            default_record = await storage.get_record(
                record_type=self.DEFAULT_MEDIATOR_RECORD_TYPE,
                record_id=self.DEFAULT_MEDIATOR_RECORD_TYPE,
            )
            return default_record
        except StorageNotFoundError:
            return None

    async def _get_default_mediator_id(self, session: ProfileSession) -> Optional[str]:
        """Retrieve the default mediator's ID from the store.

        Args:
            session: An active profile session

        Returns:
            Optional[str]: ID if present

        """
        default_record = await self._get_default_record(session)
        if default_record:
            return default_record.value

        return None

    async def get_default_mediator(self) -> Optional[MediationRecord]:
        """Retrieve default mediator from the store.

        Returns:
            Optional[MediationRecord]: retrieved default mediator or None if not set

        """
        async with self._profile.session() as session:
            mediation_id = await self._get_default_mediator_id(session)
            if mediation_id:
                return await MediationRecord.retrieve_by_id(session, mediation_id)

        return None

    async def get_default_mediator_id(self) -> Optional[str]:
        """Retrieve default mediator ID from the store.

        Returns:
            Optional[str]: retrieved default mediator ID or None if not set

        """
        async with self._profile.session() as session:
            return await self._get_default_mediator_id(session)

    async def set_default_mediator_by_id(self, mediation_id: str):
        """Set default mediator from ID."""
        async with self._profile.session() as session:
            # may throw StorageNotFoundError:
            await MediationRecord.retrieve_by_id(session, mediation_id)
            await self._set_default_mediator_id(mediation_id, session)

    async def set_default_mediator(self, record: MediationRecord):
        """Set default mediator from record."""
        async with self._profile.session() as session:
            await self._set_default_mediator_id(record.mediation_id, session)

    async def _set_default_mediator_id(self, mediation_id: str, session: ProfileSession):
        """Set the default mediator ID (internal)."""
        default_record = await self._get_default_record(session)
        storage = session.inject(BaseStorage)

        if default_record:
            await storage.update_record(default_record, mediation_id, {})
        else:
            default_record = StorageRecord(
                type=self.DEFAULT_MEDIATOR_RECORD_TYPE,
                value=mediation_id,
                id=self.DEFAULT_MEDIATOR_RECORD_TYPE,
            )
            await storage.add_record(default_record)

    async def clear_default_mediator(self):
        """Clear the stored default mediator."""
        async with self._profile.session() as session:
            storage = session.inject(BaseStorage)
            default_record = await self._get_default_record(session)
            if default_record:
                await storage.delete_record(default_record)

    async def prepare_request(
        self,
        connection_id: str,
    ) -> Tuple[MediationRecord, MediationRequest]:
        """Prepare a MediationRequest Message, saving a new mediation record.

        Args:
            connection_id (str): ID representing mediator

        Returns:
            MediationRequest: message to send to mediator

        """
        record = MediationRecord(
            role=MediationRecord.ROLE_CLIENT,
            connection_id=connection_id,
        )

        async with self._profile.session() as session:
            await record.save(session, reason="Creating new mediation request.")
        request = MediationRequest()
        return record, request

    async def request_granted(self, record: MediationRecord, grant: MediationGrant):
        """Process mediation grant message.

        Args:
            record (MediationRecord): record representing the granted mediation request
            grant (MediationGrant): message from mediator granting request

        """
        record.state = MediationRecord.STATE_GRANTED
        record.endpoint = grant.endpoint
        record.routing_keys = [
            normalize_to_did_key(key).key_id for key in grant.routing_keys
        ]
        async with self._profile.session() as session:
            await record.save(session, reason="Mediation request granted.")

    async def request_denied(self, record: MediationRecord, deny: MediationDeny):
        """Process mediation denied message.

        Args:
            record (MediationRecord): record representing the denied mediation request
            deny (MediationDeny): message from mediator denying request

        """
        record.state = MediationRecord.STATE_DENIED
        async with self._profile.session() as session:
            await record.save(session, reason="Mediation request denied.")

    async def prepare_keylist_query(
        self,
        filter_: Optional[dict] = None,
        paginate_limit: int = -1,
        paginate_offset: int = 0,
    ) -> KeylistQuery:
        """Prepare keylist query message.

        Args:
            filter_ (dict): filter for keylist query
            paginate_limit (int): paginate_limit
            paginate_offset (int): paginate_offset

        Returns:
            KeylistQuery: message to send to mediator

        """
        # TODO Handle creation of filter rather than delegating to caller?
        message = KeylistQuery(
            filter=filter_,
            paginate=KeylistQueryPaginate(paginate_limit, paginate_offset),
        )
        return message

    async def add_key(
        self, recipient_key: str, message: Optional[KeylistUpdate] = None
    ) -> KeylistUpdate:
        """Prepare a keylist update add.

        Args:
            recipient_key (str): key to add
            message (Optional[KeylistUpdate]): append update to message

        Returns:
            KeylistUpdate: Message to send to mediator to notify of key addition.

        """
        message = message or KeylistUpdate()
        message.updates.append(
            KeylistUpdateRule(recipient_key, KeylistUpdateRule.RULE_ADD)
        )
        return message

    async def remove_key(
        self, recipient_key: str, message: Optional[KeylistUpdate] = None
    ) -> KeylistUpdate:
        """Prepare keylist update remove.

        Args:
            recipient_key (str): key to remove
            message (Optional[KeylistUpdate]): append update to message

        Returns:
            KeylistUpdate: Message to send to mediator to notify of key removal.

        """
        message = message or KeylistUpdate()
        message.updates.append(
            KeylistUpdateRule(recipient_key, KeylistUpdateRule.RULE_REMOVE)
        )
        return message

    async def store_update_results(
        self, connection_id: str, results: Sequence[KeylistUpdated]
    ):
        """Store results of keylist update from keylist update response message.

        Args:
            connection_id (str): connection ID of mediator sending results
            results (Sequence[KeylistUpdated]): keylist update results
            session: An active profile session

        """
        # TODO The stored recipient keys are did:key!

        to_save: Sequence[RouteRecord] = []
        to_remove: Sequence[RouteRecord] = []

        async with self._profile.session() as session:
            for updated in results:
                if updated.result != KeylistUpdated.RESULT_SUCCESS:
                    # TODO better handle different results?
                    LOGGER.warning(
                        "Keylist update failure: %s(%s): %s",
                        updated.action,
                        updated.recipient_key,
                        updated.result,
                    )
                    continue
                if updated.action == KeylistUpdateRule.RULE_ADD:
                    # Multi-tenancy uses route record for internal relaying of wallets
                    # So the record could already exist. We update in that case
                    try:
                        record = await RouteRecord.retrieve_by_recipient_key(
                            session, updated.recipient_key
                        )
                        record.connection_id = connection_id
                        record.role = RouteRecord.ROLE_CLIENT
                    except StorageNotFoundError:
                        record = RouteRecord(
                            role=RouteRecord.ROLE_CLIENT,
                            recipient_key=updated.recipient_key,
                            connection_id=connection_id,
                        )
                    to_save.append(record)
                elif updated.action == KeylistUpdateRule.RULE_REMOVE:
                    try:
                        records = await RouteRecord.query(
                            session,
                            {
                                "role": RouteRecord.ROLE_CLIENT,
                                "connection_id": connection_id,
                                "recipient_key": updated.recipient_key,
                            },
                        )
                    except StorageNotFoundError as err:
                        LOGGER.error(
                            "No route found while processing keylist update response: %s",
                            err,
                        )
                    else:
                        if len(records) > 1:
                            LOGGER.error(
                                f"Too many ({len(records)}) routes found "
                                "while processing keylist update response"
                            )
                        record = records[0]
                        to_remove.append(record)

            for record_for_saving in to_save:
                await record_for_saving.save(session, reason="Route successfully added.")
            for record_for_removal in to_remove:
                await record_for_removal.delete_record(session)

    async def get_my_keylist(
        self, connection_id: Optional[str] = None
    ) -> Sequence[RouteRecord]:
        """Get my routed keys.

        Args:
            connection_id (Optional[str]): connection id of mediator

        Returns:
            Sequence[RouteRecord]: list of routes (the keylist)

        """
        # TODO use mediation record id instead of connection id?
        tag_filter = {"connection_id": connection_id} if connection_id else {}
        tag_filter["role"] = RouteRecord.ROLE_CLIENT
        async with self._profile.session() as session:
            return await RouteRecord.query(session, tag_filter)

    # }}}
