"""Connection complete handler under RFC 23 (DID exchange)."""

from .....config.logging import get_adapted_logger_inst
from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    RequestContext,
)

from ..manager import DIDXManager, DIDXManagerError
from ..messages.complete import DIDXComplete


class DIDXCompleteHandler(BaseHandler):
    """Handler class for connection complete message under RFC 23 (DID exchange)."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Handle connection complete under RFC 23 (DID exchange).

        Args:
            context: Request context
            responder: Responder callback
        """
        profile = context.profile
        self._logger = get_adapted_logger_inst(
            logger=self._logger,
            log_file=profile.settings.get("log.file"),
            wallet_id=profile.settings.get("wallet.id"),
        )
        self._logger.debug(f"DIDXCompleteHandler called with context {context}")
        assert isinstance(context.message, DIDXComplete)
        mgr = DIDXManager(profile)
        try:
            await mgr.accept_complete(context.message, context.message_receipt)
        except DIDXManagerError:
            # no corresponding request: no targets to send problem report; log and quit
            self._logger.exception("Error receiving connection complete")
