"""Manager for Mediation coordination."""
from typing import Sequence

from ....config.injection_context import InjectionContext
from ....core.error import BaseError

from ...routing.v1_0.models.route_record import RouteRecord

from .messages.mediate_request import MediationRequest
from .messages.mediate_grant import MediationGrant
from .messages.mediate_deny import MediationDeny
from .messages.inner.keylist_update_rule import KeylistUpdateRule
from .messages.keylist_update_response import KeylistUpdateResponse
from .messages.keylist import Keylist
from .models.mediation_record import MediationRecord


class MediationManagerError(BaseError):
    """Generic Mediation error."""


class MediationManager:
    """Class for handling Mediation."""

    def __init__(self, context: InjectionContext):
        """Initializer for Mediation Manager.
        
        Args:
            context: The context for this manager
        """
        self.context = context
        if not context:
            raise MediationManagerError("Missing request context")

    async def receive_request(self, request: MediationRequest):
        """Create a new mediation record to track this request."""
        record = MediationRecord(
            connection_id=self.context.connection_id,
            terms=request.recipient_terms
        )
        await record.save(self.context, reason="New mediation request received")

    async def grant_request(self, mediation: MediationRecord) -> MediationGrant:
        """Grant a mediation request and prepare grant message."""
        # Set state, prepare message

    async def deny_request(self, mediation: MediationRecord) -> MediationDeny:
        """Deny a mediation request and prepare a deny message.
        Args: 
            mediation:
        """
        # Set state, 
        mediation.state = MediationRecord.STATE_DENIED
        await mediation.save(self.context, reason="Mediation Request Denied")
        #prepare message
        deny = MediationDeny("Mediation Request Denied") # TODO: update message
        return deny


    async def update_keylist(
        self, updates: Sequence[KeylistUpdateRule]
    ) -> KeylistUpdateResponse:
        """Update routes defined in keylist update rules."""
        # Map to RouteUpdate, call RouteManager.update_routes
        # Map results to KeylistUpdated, put in KeylistUpdateResponse

    async def get_keylist(self, connection_id: str) -> Sequence[RouteRecord]:
        """Retrieve routes for connection."""

    async def create_keylist_query_response(
        self, keylist: Sequence[RouteRecord]
    ) -> Keylist:
        """Prepare a keylist message from keylist."""
