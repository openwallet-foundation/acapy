"""Handler for incoming invitation messages."""

from ...base_handler import BaseHandler, BaseResponder, HandlerException, RequestContext
from ..base_service import BaseIntroductionService
from ..messages.invitation import Invitation


class InvitationHandler(BaseHandler):
    """Handler for incoming invitation messages."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Message handler implementation."""
        self._logger.debug("InvitationHandler called with context %s", context)
        assert isinstance(context.message, Invitation)

        if not context.connection_active:
            raise HandlerException("No connection established for invitation message")

        svc_factory = context.service_factory
        service: BaseIntroductionService = await svc_factory.resolve_service(
            "introduction"
        )
        if service:
            await service.return_invitation(
                context.connection_record.connection_id,
                context.message,
                responder.send_outbound,
            )
        else:
            raise HandlerException(
                "Cannot handle Invitation message with no introduction service"
            )
