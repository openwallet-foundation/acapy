"""Connection complete handler under RFC 23 (DID exchange)."""

import logging

from .....config.logging import get_logger_inst
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
        _logger: logging.Logger = get_logger_inst(
            profile=context.profile,
            logger_name=__name__,
        )
        _logger.debug(f"DIDXCompleteHandler called with context {context}")
        assert isinstance(context.message, DIDXComplete)

        profile = context.profile
        mgr = DIDXManager(profile)
        try:
            await mgr.accept_complete(context.message, context.message_receipt)
        except DIDXManagerError:
            # no corresponding request: no targets to send problem report; log and quit
            _logger.exception("Error receiving connection complete")
