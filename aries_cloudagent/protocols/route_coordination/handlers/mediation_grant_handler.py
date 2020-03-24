"""Mediation grant handler."""


from ....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext
)

from ..messages.mediation_grant import MediationGrant
from ..manager import RouteCoordinationManager


class MediationGrantHandler(BaseHandler):
    """Handler for mediation grant from mediator."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Message handler logic for mediation grant.

        Args:
            context: request context
            responder: responder callback

        """
        self._logger.debug("MediationGrantHandler called with context %s", context)
        assert isinstance(context.message, MediationGrant)
        self._logger.info(
            "Received mediation grant message: %s",
            context.message.serialize(as_string=True)
        )

        if not context.connection_ready:
            raise HandlerException("No connection established for mediation request")

        routing_manager = RouteCoordinationManager(context)

        await routing_manager.receive_mediation_grant()
