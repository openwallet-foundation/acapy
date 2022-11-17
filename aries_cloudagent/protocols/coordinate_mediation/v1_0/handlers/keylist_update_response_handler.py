"""Handler for keylist-update-response message."""

from .....core.profile import Profile
from .....messaging.base_handler import BaseHandler, HandlerException
from .....messaging.request_context import RequestContext
from .....messaging.responder import BaseResponder
from .....storage.error import StorageNotFoundError
from .....wallet.error import WalletNotFoundError
from ..manager import MediationManager
from ..messages.keylist_update_response import KeylistUpdateResponse
from ..route_manager import RouteManager


class KeylistUpdateResponseHandler(BaseHandler):
    """Handler for keylist-update-response message."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Handle keylist-update-response message."""
        self._logger.debug(
            "%s called with context %s", self.__class__.__name__, context
        )
        assert isinstance(context.message, KeylistUpdateResponse)

        if not context.connection_ready:
            raise HandlerException("Invalid mediation request: no active connection")

        mgr = MediationManager(context.profile)
        await mgr.store_update_results(
            context.connection_record.connection_id, context.message.updated
        )
        await self.notify_keylist_updated(
            context.profile, context.connection_record.connection_id, context.message
        )

    async def notify_keylist_updated(
        self, profile: Profile, connection_id: str, response: KeylistUpdateResponse
    ):
        """Notify of keylist update response received."""
        route_manager = profile.inject(RouteManager)
        self._logger.debug(
            "Retrieving connection ID from route manager of type %s",
            type(route_manager).__name__,
        )
        try:
            key_to_connection = {
                updated.recipient_key: await route_manager.connection_from_recipient_key(
                    profile, updated.recipient_key
                )
                for updated in response.updated
            }
        except (StorageNotFoundError, WalletNotFoundError) as err:
            raise HandlerException(
                "Unknown recipient key received in keylist update response"
            ) from err

        await profile.notify(
            MediationManager.KEYLIST_UPDATED_EVENT,
            {
                "connection_id": connection_id,
                "thread_id": response._thread_id,
                "updated": [update.serialize() for update in response.updated],
                "mediated_connections": {
                    key: conn.connection_id for key, conn in key_to_connection.items()
                },
            },
        )
