"""Handler for incoming disclose messages."""

from .....config.logging import get_adapted_logger_inst
from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    RequestContext,
    HandlerException,
)

from ..manager import V20DiscoveryMgr
from ..messages.disclosures import Disclosures


class DisclosuresHandler(BaseHandler):
    """Handler for incoming disclose messages."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Message handler implementation."""
        profile = context.profile
        self._logger = get_adapted_logger_inst(
            logger=self._logger,
            log_file=profile.settings.get("log.file"),
            wallet_id=profile.settings.get("wallet.id"),
        )
        self._logger.debug("DiscloseHandler called with context %s", context)
        assert isinstance(context.message, Disclosures)
        if not context.connection_ready:
            raise HandlerException(
                "Received disclosures message from inactive connection"
            )
        mgr = V20DiscoveryMgr(profile)
        await mgr.receive_disclose(
            context.message, connection_id=context.connection_record.connection_id
        )
