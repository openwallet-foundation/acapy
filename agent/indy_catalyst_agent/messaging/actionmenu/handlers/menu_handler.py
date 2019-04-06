"""Action menu message handler."""

from ...base_handler import BaseHandler, BaseResponder, RequestContext
from ..messages.menu import Menu


class MenuHandler(BaseHandler):
    """Message handler class for action menus."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Message handler logic for action menus.

        Args:
            context: request context
            responder: responder callback
        """
        self._logger.debug(f"MenuHandler called with context {context}")
        assert isinstance(context.message, Menu)

        self._logger.info("Received action menu: %s", context.message)

        context.connection_record.active_menu = context.message.serialize()
        await context.connection_record.save(context.storage)
