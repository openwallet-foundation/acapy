"""Action menu perform request message handler."""

from ...base_handler import BaseHandler, BaseResponder, RequestContext
from ..messages.perform import Perform


class PerformHandler(BaseHandler):
    """Message handler class for action menu perform requests."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Message handler logic for action menu perform requests.

        Args:
            context: request context
            responder: responder callback
        """
        self._logger.debug(f"PerformHandler called with context {context}")
        assert isinstance(context.message, Perform)

        self._logger.info("Received action menu perform request")

        # TODO: if menu service is registered, ask it to perform the action
