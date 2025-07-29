"""Action menu message handler."""

from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext,
)
from ..messages.menu import Menu
from ..util import save_connection_menu


class MenuHandler(BaseHandler):
    """Message handler class for action menus."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Message handler logic for action menus.

        Args:
            context: request context
            responder: responder callback
        """
        self._logger.debug(f"MenuHandler called with context {context}")
        assert isinstance(context.message, Menu)

        if not context.connection_ready:
            raise HandlerException("No connection established")

        self._logger.info(f"Received action menu: {context.message}")

        await save_connection_menu(
            context.message, context.connection_record.connection_id, context
        )
        self._logger.debug(
            f"Updated action menu on connection: {context.connection_record.connection_id}"
        )
