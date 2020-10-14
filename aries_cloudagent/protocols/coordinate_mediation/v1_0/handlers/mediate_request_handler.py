"""Handler for incoming route-update-request messages."""

from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext,
)

from ..manager import MediationManager
from ..messages.mediate_request import MediationRequest


class MediationRequestHandler(BaseHandler):
    """Handler for incoming route-update-request messages."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Message handler implementation."""
        self._logger.debug(
            "%s called with context %s", self.__class__.__name__, context
        )
        assert isinstance(context.message, MediationRequest)

        if not context.connection_ready:
            raise HandlerException("Invalid mediation request: no active connection")

        mgr = MediationManager(context)
        record = await mgr.receive_request(context.message)
        if context.settings.get("mediation.open", False):
            grant = await mgr.grant_request(record)
            await responder.send_reply(grant)
