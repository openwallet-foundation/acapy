"""Mediation request handler."""


from ....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext
)

from ..messages.mediation_request import MediationRequest
from ..manager import RouteCoordinationManager


class MediationRequestHandler(BaseHandler):
    """Request handler for mediation requests."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Message handler logic for mediation request.

        Args:
            context: request context
            responder: responder callback

        """
        self._logger.debug("MediationRequestHandler called with context %s", context)
        assert isinstance(context.message, MediationRequest)
        self._logger.info(
            "Received mediation request message: %s",
            context.message.serialize(as_string=True)
        )

        if not context.connection_ready:
            raise HandlerException("No connection established for mediation request")

        routing_manager = RouteCoordinationManager(context)

        await routing_manager.receive_request()
