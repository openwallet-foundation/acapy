"""Manager for Mediation coordination."""
import json
from typing import Sequence, Optional

from ....config.injection_context import InjectionContext
from ....core.error import BaseError
from ....wallet.base import BaseWallet, DIDInfo
from ....storage.record import StorageRecord
from ....storage.base import BaseStorage
from ....storage.error import StorageNotFoundError

from ...routing.v1_0.models.route_record import RouteRecord
from ...routing.v1_0.manager import RoutingManager
from ...routing.v1_0.models.route_update import RouteUpdate
from ...routing.v1_0.models.route_updated import RouteUpdated

from .messages.mediate_request import MediationRequest
from .messages.mediate_grant import MediationGrant
from .messages.mediate_deny import MediationDeny
from .messages.inner.keylist_update_rule import KeylistUpdateRule
from .messages.inner.keylist_updated import KeylistUpdated
from .messages.inner.keylist_key import KeylistKey
from .messages.keylist_update_response import KeylistUpdateResponse
from .messages.keylist import Keylist
from .models.mediation_record import MediationRecord


class MediationManagerError(BaseError):
    """Generic Mediation error."""


class MediationManager:
    """Class for handling Mediation."""
    RECORD_TYPE = "routing_did"

    def __init__(self, context: InjectionContext):
        """Initializer for Mediation Manager.

        Args:
            context: The context for this manager
        """
        if not context:
            raise MediationManagerError("Missing request context")

        self.context = context

    async def _retrieve_routing_did(self) -> Optional[DIDInfo]:
        """Get the routing DID out of the wallet if it exists"""
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
        """Create routing DID."""
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
        """Create a new mediation record to track this request."""
        # TODO: Determine if terms are acceptable
        record = MediationRecord(
            connection_id=self.context.connection_record.connection_id,
            mediator_terms=request.mediator_terms,
            recipient_terms=request.recipient_terms
        )
        await record.save(self.context, reason="New mediation request received")
        return record

    async def grant_request(self, mediation: MediationRecord) -> MediationGrant:
        """Grant a mediation request and prepare grant message."""
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
        """Deny a mediation request and prepare a deny message."""
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
        """Update routes defined in keylist update rules."""
        # TODO: Don't borrow logic from RoutingManager
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
        updates = map(rule_to_update, updates)
        updated = await route_mgr.update_routes(record.connection_id, updates)
        updated = map(updated_to_keylist_updated, updated)
        return KeylistUpdateResponse(updated=updated)

    async def get_keylist(self, record: MediationRecord) -> Sequence[RouteRecord]:
        """Retrieve routes for connection."""
        route_mgr = RoutingManager(self.context)
        return await route_mgr.get_routes(record.connection_id)

    async def create_keylist_query_response(
        self, keylist: Sequence[RouteRecord]
    ) -> Keylist:
        """Prepare a keylist message from keylist."""
        keys = list(map(
            lambda key: KeylistKey(recipient_key=key.recipient_key), keylist
        ))
        return Keylist(keys=keys, pagination=None)
