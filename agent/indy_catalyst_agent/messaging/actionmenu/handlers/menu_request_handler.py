"""Action menu request message handler."""

from ...base_handler import BaseHandler, BaseResponder, RequestContext
from ..messages.menu_request import MenuRequest


class MenuRequestHandler(BaseHandler):
    """Message handler class for action menu requests."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Message handler logic for action menu requests.

        Args:
            context: request context
            responder: responder callback
        """
        self._logger.debug(f"MenuRequestHandler called with context {context}")
        assert isinstance(context.message, MenuRequest)

        self._logger.info("Received action menu request")

        # TODO: if menu service is registered, ask it to generate a menu
