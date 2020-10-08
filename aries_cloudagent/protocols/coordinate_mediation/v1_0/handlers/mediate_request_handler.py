"""Handler for incoming route-update-request messages."""

from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext,
)

from ..manager import RoutingManager
from ..messages.mediate_request import MediationRequest
from ..messages.mediate_grant import MediationGrant


class MediationRequestHandler(BaseHandler):
    """Handler for incoming route-update-request messages."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Message handler implementation."""
        self._logger.debug(
            "%s called with context %s", self.__class__.__name__, context
        )
        assert isinstance(context.message, MediationRequest)

        if not context.connection_ready:
            raise HandlerException("Cannot update routes: no active connection")

        mgr = RoutingManager(context)
        updated = await mgr.update_routes(
            context.connection_record.connection_id, context.message.updates
        )
        response = MediationGrant(
            endpoint=context.settings.get("default_endpoint"),
            routing_keys=None
        )
        await responder.send_reply(response)
