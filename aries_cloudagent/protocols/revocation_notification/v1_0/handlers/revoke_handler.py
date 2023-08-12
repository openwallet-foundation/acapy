"""Handler for revoke message."""

import logging

from .....config.logging import get_logger_inst
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
        _logger: logging.Logger = get_logger_inst(
            profile=context.profile,
            logger_name=__name__,
        )
        _logger.debug(
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
