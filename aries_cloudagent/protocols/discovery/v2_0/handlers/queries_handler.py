"""Handler for incoming queries messages."""

from .....config.logging import get_adapted_logger_inst
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
        profile = context.profile
        self._logger = get_adapted_logger_inst(
            logger=self._logger,
            log_file=profile.settings.get("log.file"),
            wallet_id=profile.settings.get("wallet.id"),
        )
        self._logger.debug("QueryHandler called with context %s", context)
        assert isinstance(context.message, Queries)
        mgr = V20DiscoveryMgr(profile)
        reply = await mgr.receive_query(context.message)
        reply.assign_thread_from(context.message)
        reply.assign_trace_from(context.message)
        await responder.send_reply(reply)
