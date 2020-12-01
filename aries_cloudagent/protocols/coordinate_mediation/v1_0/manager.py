"""Manager for Mediation coordination."""
import json
from typing import Optional, Sequence

from ....config.injection_context import InjectionContext
from ....core.error import BaseError
from ....storage.base import BaseStorage
from ....storage.error import StorageNotFoundError
from ....storage.record import StorageRecord
from ....wallet.base import BaseWallet, DIDInfo
from ...routing.v1_0.manager import RoutingManager
from ...routing.v1_0.models.route_record import RouteRecord
from ...routing.v1_0.models.route_update import RouteUpdate
from ...routing.v1_0.models.route_updated import RouteUpdated
from .messages.inner.keylist_key import KeylistKey
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


class MediationManagerError(BaseError):
    """Generic Mediation error."""


class MediationManager:
    """Class for handling Mediation.

    MediationManager creates or retrieves a routing DID as a means to hand out
    a consistent routing key to mediation clients.
    """

    RECORD_TYPE = "routing_did"

    def __init__(self, context: InjectionContext):
        """Initialize Mediation Manager.

        Args:
            context: The context for this manager
        """
        if not context:
            raise MediationManagerError("Missing request context")

        self.context = context

    # Role: Server {{{

    async def _retrieve_routing_did(self) -> Optional[DIDInfo]:
        """Retrieve routing DID from the store.

        Returns:
            Optional[DIDInfo]: retrieved DID info or None if not found
        """
        storage: BaseStorage = await self.context.inject(BaseStorage)
        try:
            record = await storage.get_record(
                record_type=self.RECORD_TYPE,
                record_id=self.RECORD_TYPE
            )
            info = json.loads(record.value)
            info.update(record.tags)
            return DIDInfo(**info)
        except StorageNotFoundError:
            return None

    async def _create_routing_did(self) -> DIDInfo:
        """Create routing DID.

        Returns:
            DIDInfo: created routing DID info
        """
        wallet: BaseWallet = await self.context.inject(BaseWallet)
        storage: BaseStorage = await self.context.inject(BaseStorage)
        info: DIDInfo = await wallet.create_local_did(metadata={"type": "routing_did"})
        record = StorageRecord(
            type=self.RECORD_TYPE,
            value=json.dumps({"verkey": info.verkey, "metadata": info.metadata}),
            tags={"did": info.did},
            id=self.RECORD_TYPE
        )
        await storage.add_record(record)
        return info

    async def receive_request(self, request: MediationRequest) -> MediationRecord:
        """Create a new mediation record to track this request.

        Args:
            request (MediationRequest): request message

        Returns:
            MediationRecord: record created during receipt of request.
        """
        if await MediationRecord.exists_for_connection_id(
            self.context, self.context.connection_record.connection_id
        ):
            raise MediationManagerError('Mediation Record already exists for connection')

        # TODO: Determine if terms are acceptable
        record = MediationRecord(
            connection_id=self.context.connection_record.connection_id,
            mediator_terms=request.mediator_terms,
            recipient_terms=request.recipient_terms
        )
        await record.save(self.context, reason="New mediation request received")
        return record

    async def grant_request(self, mediation: MediationRecord) -> MediationGrant:
        """Grant a mediation request and prepare grant message.

        Args:
            mediation (MediationRecord): mediation record to grant

        Returns:
            MediationGrant: message to return to grantee
        """
        routing_did: DIDInfo = await self._retrieve_routing_did()
        if not routing_did:
            routing_did = await self._create_routing_did()

        mediation.state = MediationRecord.STATE_GRANTED
        await mediation.save(self.context, reason="Mediation request granted")
        grant = MediationGrant(
            endpoint=self.context.settings.get("default_endpoint"),
            routing_keys=[routing_did.verkey]
        )
        return grant

    async def deny_request(
        self,
        mediation: MediationRecord,
        *,
        mediator_terms: Sequence[str] = None,
        recipient_terms: Sequence[str] = None
    ) -> MediationDeny:
        """Deny a mediation request and prepare a deny message.

        Args:
            mediation (MediationRecord): mediation record to deny
            mediator_terms (Sequence[str]): updated mediator terms to return to
            requester.
            recipient_terms (Sequence[str]): updated recipient terms to return to
            requester.

        Returns:
            MediationDeny: message to return to denied client.
        """
        mediation.state = MediationRecord.STATE_DENIED
        await mediation.save(self.context, reason="Mediation request denied")
        deny = MediationDeny(
            mediator_terms=mediator_terms,
            recipient_terms=recipient_terms
        )
        return deny

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
        # TODO: Don't borrow logic from RoutingManager
        # Bidirectional mapping of KeylistUpdateRules to RouteUpdate actions
        action_map = {
            KeylistUpdateRule.RULE_ADD: RouteUpdate.ACTION_CREATE,
            KeylistUpdateRule.RULE_REMOVE: RouteUpdate.ACTION_DELETE,
            RouteUpdate.ACTION_DELETE: KeylistUpdateRule.RULE_REMOVE,
            RouteUpdate.ACTION_CREATE: KeylistUpdateRule.RULE_ADD
        }

        def rule_to_update(rule: KeylistUpdateRule):
            return RouteUpdate(
                recipient_key=rule.recipient_key,
                action=action_map[rule.action]
            )

        def updated_to_keylist_updated(updated: RouteUpdated):
            return KeylistUpdated(
                recipient_key=updated.recipient_key,
                action=action_map[updated.action],
                result=updated.result
            )

        route_mgr = RoutingManager(self.context)
        # Map keylist update rules to route updates
        updates = map(rule_to_update, updates)
        updated = await route_mgr.update_routes(record.connection_id, updates)
        # Map RouteUpdated to KeylistUpdated
        updated = map(updated_to_keylist_updated, updated)
        return KeylistUpdateResponse(updated=updated)

    async def get_keylist(self, record: MediationRecord) -> Sequence[RouteRecord]:
        """Retrieve keylist for mediation client.

        Args:
            record (MediationRecord): record associated with client keylist

        Returns:
            Sequence[RouteRecord]: sequence of routes (the keylist)
        """
        route_mgr = RoutingManager(self.context)
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
        keys = list(map(
            lambda key: KeylistKey(recipient_key=key.recipient_key), keylist
        ))
        return Keylist(keys=keys, pagination=None)

    # }}}

    # Role: Client {{{

    async def prepare_request(
        self,
        connection_id: str,
        mediator_terms: Sequence[str] = None,
        recipient_terms: Sequence[str] = None
    ) -> MediationRequest:
        """Prepare a MediationRequest Message, saving a new mediation record.

        Args:
            connection_id (str): ID representing mediator
            mediator_terms (Sequence[str]): mediator_terms
            recipient_terms (Sequence[str]): recipient_terms

        Returns:
            MediationRequest: message to send to mediator
        """
        record = MediationRecord(
            role=MediationRecord.ROLE_CLIENT,
            connection_id=connection_id,
            mediator_terms=mediator_terms,
            recipient_terms=recipient_terms
        )
        await record.save(self.context, reason="Creating new mediation request.")
        return MediationRequest(
            mediator_terms=mediator_terms,
            recipient_terms=recipient_terms
        )

    async def request_granted(
        self,
        record: MediationRecord
    ):
        """Process mediation grant message.

        Args:
            record (MediationRecord): record representing the granted mediation request
        """
        record.state = MediationRecord.STATE_GRANTED
        await record.save(self.context, reason="Mediation request granted.")
        # TODO Store endpoint and routing key for later use.

    async def request_denied(
        self,
        record: MediationRecord
    ):
        """Process mediation denied message.

        Args:
            record (MediationRecord): record representing the denied mediation request
        """
        record.state = MediationRecord.STATE_DENIED
        await record.save(self.context, reason="Mediation request denied.")
        # TODO Remove endpoint and routing key.

    async def prepare_keylist_query(
        self,
        filter_: dict = None,
        paginate_limit: int = -1,
        paginate_offset: int = 0
    ) -> KeylistQuery:
        """Prepare keylist query message.

        Args:
            filter_ (dict): filter_ for keylist query
            paginate_limit (int): paginate_limit
            paginate_offset (int): paginate_offset

        Returns:
            KeylistQuery: message to send to mediator
        """
        # TODO Handle creation of rather than delegating to caller?
        message = KeylistQuery(
            filter=filter_,
            paginate={
                'limit': paginate_limit, 'offset': paginate_offset
            }
        )
        return message

    async def add_key(
        self,
        recipient_key: str,
        message: Optional[KeylistUpdate] = None
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
        self,
        recipient_key: str,
        message: KeylistUpdate = None
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

    async def get_my_keylist(
        self,
        connection_id: Optional[str] = None
    ) -> Sequence[RouteRecord]:
        """Get my routed keys.

        Args:
            connection_id (Optional[str]): connection id of mediator

        Returns:
            Sequence[RouteRecord]: list of routes (the keylist)
        """
        # TODO use mediation record id instead of connection id?
        tag_filter = {'connection_id': connection_id} if connection_id else {}
        tag_filter['role'] = RouteRecord.ROLE_CLIENT
        return await RouteRecord.query(self.context, tag_filter)

    # }}}
