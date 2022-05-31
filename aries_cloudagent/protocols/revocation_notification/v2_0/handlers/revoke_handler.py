"""Handler for revoke message."""

from .....messaging.base_handler import BaseHandler
from .....messaging.request_context import RequestContext
from .....messaging.responder import BaseResponder

from ..messages.revoke import Revoke


class RevokeHandler(BaseHandler):
    """Handler for revoke message."""

    RECIEVED_TOPIC = "acapy::revocation-notification-v2::received"
    WEBHOOK_TOPIC = "acapy::webhook::revocation-notification-v2"

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Handle revoke message."""
        assert isinstance(context.message, Revoke)
        self._logger.debug(
            "Received notification of revocation for %s cred %s with comment: %s",
            context.message.revocation_format,
            context.message.credential_id,
            context.message.comment,
        )
        # Emit a webhook
        if context.settings.get("revocation.monitor_notification"):
            await context.profile.notify(
                self.WEBHOOK_TOPIC,
                {
                    "revocation_format": context.message.revocation_format,
                    "credential_id": context.message.credential_id,
                    "comment": context.message.comment,
                },
            )

        # Emit an event
        await context.profile.notify(
            self.RECIEVED_TOPIC,
            {
                "revocation_format": context.message.revocation_format,
                "credential_id": context.message.credential_id,
                "comment": context.message.comment,
            },
        )
