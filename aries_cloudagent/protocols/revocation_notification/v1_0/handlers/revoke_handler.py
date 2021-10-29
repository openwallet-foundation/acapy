"""Handler for revoke message."""

from .....messaging.base_handler import BaseHandler
from .....messaging.request_context import RequestContext
from .....messaging.responder import BaseResponder

from ..messages.revoke import Revoke


class RevokeHandler(BaseHandler):
    """Handler for revoke message."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Handle revoke message."""
        assert isinstance(context.message, Revoke)
        self._logger.debug(
            "Received notification of revocation for cred issued in thread %s "
            "with comment: %s",
            context.message.thread_id,
            context.message.comment,
        )
        # Emit a webhook
        if context.settings.get("revocation.monitor_notification"):
            await context.profile.notify(
                "acapy::webhook::revocation-notification",
                {
                    "thread_id": context.message.thread_id,
                    "comment": context.message.comment,
                },
            )

        # Emit an event
        await context.profile.notify(
            "acapy::revocation-notification::received",
            {
                "thread_id": context.message.thread_id,
                "comment": context.message.comment,
            },
        )
