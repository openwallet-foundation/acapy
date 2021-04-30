"""Handler for incoming invitation messages."""

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
        self._logger.debug("InvitationHandler called with context %s", context)
        assert isinstance(context.message, IntroInvitation)

        if not context.connection_ready:
            raise HandlerException("No connection established for invitation message")

        service: BaseIntroductionService = context.inject(
            BaseIntroductionService, required=False
        )
        if service:
            await service.return_invitation(
                context.connection_record.connection_id,
                context.message,
                await context.session(),
                responder.send,
            )
        else:
            raise HandlerException(
                "Cannot handle Invitation message with no introduction service"
            )
