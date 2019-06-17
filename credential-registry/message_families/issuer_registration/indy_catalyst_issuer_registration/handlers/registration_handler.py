"""Issuer registration handler."""

from indy_catalyst_agent.messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    RequestContext,
)
from ..messages.register import IssuerRegistration
from ..manager import IssuerRegistrationManager


class IssuerRegistrationHandlerHandler(BaseHandler):
    """Message handler class for issuer registration."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Message handler logic for issuer registration.

        Args:
            context: request context
            responder: responder callback
        """
        self._logger.debug(
            f"IssuerRegistrationHandlerHandler called with context {context}"
        )
        assert isinstance(context.message, IssuerRegistration)

        self._logger.info("Received issuer registration: %s", context.message)

        issuer_registration_manager = IssuerRegistrationManager(context)

        await issuer_registration_manager.receive_registration(
            context.connection_record.connection_id, context.message
        )
