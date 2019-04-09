"""Basic message handler."""

from ...base_handler import BaseHandler, BaseResponder, RequestContext

from ..manager import PresentationManager
from ..messages.presentation_request import PresentationRequest


class PresentationRequestHandler(BaseHandler):
    """Message handler class for presentation requests."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Message handler logic for presentation requests.

        Args:
            context: request context
            responder: responder callback
        """
        self._logger.debug(f"PresentationRequestHandler called with context {context}")

        assert isinstance(context.message, PresentationRequest)

        self._logger.info("Received presentation request: %s", context.message.request)

        presentation_manager = PresentationManager(context)

        await presentation_manager.receive_request(
            context.message, context.connection_record.connection_id
        )
