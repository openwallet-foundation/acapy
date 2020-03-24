"""Mediation grant handler."""


from ....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext
)

from ..messages.mediation_deny import MediationDeny
from ..manager import RouteCoordinationManager


class MediationDenyHandler(BaseHandler):
    """Handler for mediation deny from mediator."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Message handler logic for mediation deny.

        Args:
            context: request context
            responder: responder callback

        """
        self._logger.debug("MediationDenyHandler called with context %s", context)
        assert isinstance(context.message, MediationDeny)
        self._logger.info(
            "Received mediation deny message: %s",
            context.message.serialize(as_string=True)
        )

        if not context.connection_ready:
            raise HandlerException("No connection established for mediation request")

        routing_manager = RouteCoordinationManager(context)

        await routing_manager.receive_mediation_deny()
