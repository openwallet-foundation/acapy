"""Action menu perform request message handler."""

import logging

from .....config.logging import get_logger_inst
from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    RequestContext,
)

from ..base_service import BaseMenuService
from ..messages.perform import Perform


class PerformHandler(BaseHandler):
    """Message handler class for action menu perform requests."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Message handler logic for action menu perform requests.

        Args:
            context: request context
            responder: responder callback
        """
        _logger: logging.Logger = get_logger_inst(
            profile=context.profile,
            logger_name=__name__,
        )
        _logger.debug("PerformHandler called with context %s", context)
        assert isinstance(context.message, Perform)

        _logger.info("Received action menu perform request")

        service: BaseMenuService = context.inject_or(BaseMenuService)
        if service:
            reply = await service.perform_menu_action(
                context.profile,
                context.message.name,
                context.message.params or {},
                context.connection_record,
                context.message._thread_id,
            )
            if reply:
                await responder.send_reply(reply)
        else:
            # send problem report?
            pass
