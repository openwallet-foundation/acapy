"""Handler for incoming route-update-request messages."""

from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext,
)

from ..manager import RoutingManager
from ..messages.keylist_update_request import KeylistUpdate
from ..messages.keylist_update_response import KeylistUpdateResponse


class KeylistUpdateHandler(BaseHandler):
    """Handler for incoming route-update-request messages."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Message handler implementation."""
        self._logger.debug(
            "%s called with context %s", self.__class__.__name__, context
        )
        assert isinstance(context.message, KeylistUpdate)

        if not context.connection_ready:
            raise HandlerException("Cannot update routes: no active connection")

        mgr = RoutingManager(context)
        updated = await mgr.update_routes(
            context.connection_record.connection_id, context.message.updates
        )
        response = KeylistUpdateResponse(updated=updated)
        await responder.send_reply(response)
