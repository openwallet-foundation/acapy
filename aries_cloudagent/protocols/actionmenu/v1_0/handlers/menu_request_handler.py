"""Action menu request message handler."""

from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    RequestContext,
)

from ..base_service import BaseMenuService
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
        self._logger.debug("MenuRequestHandler called with context %s", context)
        assert isinstance(context.message, MenuRequest)

        self._logger.info("Received action menu request")

        service: BaseMenuService = context.inject(BaseMenuService, required=False)
        if service:
            menu = await service.get_active_menu(
                context.connection_record, context.message._thread_id
            )
            if menu:
                await responder.send_reply(menu)
        else:
            # send problem report?
            pass
