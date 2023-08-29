"""Handler for incoming invitation messages."""

from typing import Optional

from .....config.logging import get_adapted_logger_inst
from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext,
)

from ..base_service import BaseIntroductionService
from ..messages.invitation import Invitation as IntroInvitation


class InvitationHandler(BaseHandler):
    """Handler for incoming invitation messages."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Message handler implementation."""
        profile = context.profile
        self._logger = get_adapted_logger_inst(
            logger=self._logger,
            log_file=profile.settings.get("log.file"),
            wallet_id=profile.settings.get("wallet.id"),
        )
        self._logger.debug("InvitationHandler called with context %s", context)
        assert isinstance(context.message, IntroInvitation)

        if not context.connection_ready:
            raise HandlerException("No connection established for invitation message")

        service: Optional[BaseIntroductionService] = context.inject_or(
            BaseIntroductionService
        )
        if service:
            async with context.profile.session() as session:
                await service.return_invitation(
                    context.connection_record.connection_id,
                    context.message,
                    session,
                    responder.send,
                )
        else:
            raise HandlerException(
                "Cannot handle Invitation message with no introduction service"
            )
