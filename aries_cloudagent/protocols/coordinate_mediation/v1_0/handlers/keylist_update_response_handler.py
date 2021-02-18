"""Handler for keylist-update-response message."""
from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext,
)
from ..messages.keylist_update_response import KeylistUpdateResponse
from ..manager import MediationManager


class KeylistUpdateResponseHandler(BaseHandler):
    """Handler for keylist-update-response message."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Handle keylist-update-response message."""
        self._logger.debug(
            "%s called with context %s", self.__class__.__name__, context
        )
        assert isinstance(context.message, KeylistUpdateResponse)

        if not context.connection_ready:
            raise HandlerException("Invalid mediation request: no active connection")

        mgr = MediationManager(context.profile)
        await mgr.store_update_results(
            context.connection_record.connection_id, context.message.updated
        )
