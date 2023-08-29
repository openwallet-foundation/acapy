"""Handler for revoke message."""

from .....config.logging import get_adapted_logger_inst
from .....messaging.base_handler import BaseHandler
from .....messaging.request_context import RequestContext
from .....messaging.responder import BaseResponder

from ..messages.revoke import Revoke


class RevokeHandler(BaseHandler):
    """Handler for revoke message."""

    RECIEVED_TOPIC = "acapy::revocation-notification::received"
    WEBHOOK_TOPIC = "acapy::webhook::revocation-notification"

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Handle revoke message."""
        assert isinstance(context.message, Revoke)
        profile = context.profile
        self._logger = get_adapted_logger_inst(
            logger=self._logger,
            log_file=profile.settings.get("log.file"),
            wallet_id=profile.settings.get("wallet.id"),
        )
        self._logger.debug(
            "Received notification of revocation for cred issued in thread %s "
            "with comment: %s",
            context.message.thread_id,
            context.message.comment,
        )
        # Emit a webhook
        if context.settings.get("revocation.monitor_notification"):
            await context.profile.notify(
                self.WEBHOOK_TOPIC,
                {
                    "thread_id": context.message.thread_id,
                    "comment": context.message.comment,
                },
            )

        # Emit an event
        await context.profile.notify(
            self.RECIEVED_TOPIC,
            {
                "thread_id": context.message.thread_id,
                "comment": context.message.comment,
            },
        )
