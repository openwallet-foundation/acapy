"""Aries#0037 v1.0 presentation handler."""


from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext,
)

from ..manager import PresentationManager
from ..messages.presentation import Presentation


class PresentationHandler(BaseHandler):
    """Message handler class for presentations."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Message handler logic for presentations.

        Args:
            context: request context
            responder: responder callback
        """
        self._logger.debug(f"PresentationHandler called with context {context}")
        assert isinstance(context.message, Presentation)
        self._logger.info(f"Received presentation: {context.message.indy_proof(0)}")

        if not context.connection_ready:
            raise HandlerException("No connection established for presentation request")

        presentation_manager = PresentationManager(context)

        presentation_exchange_record = await presentation_manager.receive_presentation()

        if context.settings.get("debug.auto_verify_presentation"):
            await presentation_manager.verify_presentation(presentation_exchange_record)
