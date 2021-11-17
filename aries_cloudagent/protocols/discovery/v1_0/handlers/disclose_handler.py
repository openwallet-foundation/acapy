"""Handler for incoming disclose messages."""

from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    RequestContext,
)

from ..manager import V10DiscoveryMgr
from ..messages.disclose import Disclose


class DiscloseHandler(BaseHandler):
    """Handler for incoming disclose messages."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Message handler implementation."""
        self._logger.debug("DiscloseHandler called with context %s", context)
        assert isinstance(context.message, Disclose)
        profile = context.profile
        mgr = V10DiscoveryMgr(profile)
        await mgr.receive_disclose(context.message)
