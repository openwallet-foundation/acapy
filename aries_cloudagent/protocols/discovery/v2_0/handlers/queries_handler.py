"""Handler for incoming queries messages."""

import logging

from .....config.logging import get_logger_inst
from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    RequestContext,
)

from ..manager import V20DiscoveryMgr
from ..messages.queries import Queries


class QueriesHandler(BaseHandler):
    """Handler for incoming queries messages."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Message handler implementation."""
        _logger: logging.Logger = get_logger_inst(
            profile=context.profile,
            logger_name=__name__,
        )
        _logger.debug("QueryHandler called with context %s", context)
        assert isinstance(context.message, Queries)
        profile = context.profile
        mgr = V20DiscoveryMgr(profile)
        reply = await mgr.receive_query(context.message)
        reply.assign_thread_from(context.message)
        reply.assign_trace_from(context.message)
        await responder.send_reply(reply)
