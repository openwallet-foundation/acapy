"""Handler for incoming query messages."""

from .....config.logging import get_adapted_logger_inst
from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    RequestContext,
)

from ..manager import V10DiscoveryMgr
from ..messages.query import Query


class QueryHandler(BaseHandler):
    """Handler for incoming query messages."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Message handler implementation."""
        profile = context.profile
        self._logger = get_adapted_logger_inst(
            logger=self._logger,
            log_file=profile.settings.get("log.file"),
            wallet_id=profile.settings.get("wallet.id"),
        )
        self._logger.debug("QueryHandler called with context %s", context)
        assert isinstance(context.message, Query)
        mgr = V10DiscoveryMgr(profile)
        reply = await mgr.receive_query(context.message)
        reply.assign_thread_from(context.message)
        reply.assign_trace_from(context.message)
        await responder.send_reply(reply)
