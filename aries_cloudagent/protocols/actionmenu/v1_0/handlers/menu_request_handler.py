"""Action menu request message handler."""

from .....config.logging import get_adapted_logger_inst
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
        """Message handler logic for action menu requests.

        Args:
            context: request context
            responder: responder callback
        """
        profile = context.profile
        self._logger = get_adapted_logger_inst(
            logger=self._logger,
            log_file=profile.settings.get("log.file"),
            wallet_id=profile.settings.get("wallet.id"),
        )
        self._logger.debug("MenuRequestHandler called with context %s", context)
        assert isinstance(context.message, MenuRequest)

        self._logger.info("Received action menu request")

        service: BaseMenuService = context.inject_or(BaseMenuService)
        if service:
            menu = await service.get_active_menu(
                context.profile,
                context.connection_record,
                context.message._thread_id,
            )
            if menu:
                await responder.send_reply(menu)
        else:
            # send problem report?
            pass
