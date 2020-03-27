"""Keylist update response handler."""


from ....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext
)

from ..messages.keylist_update_response import KeylistUpdateResponse
from ..manager import RouteCoordinationManager


class KeylistUpdateResponseHandler(BaseHandler):
    """Handler for keylist update response."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Message handler logic for keylist update response.

        Args:
            context: request context
            responder: responder callback

        """
        self._logger.debug(
            "KeylistUpdateResponseHandler called with context %s",
            context
        )
        assert isinstance(context.message, KeylistUpdateResponse)
        self._logger.info(
            "Received keylist update response message: %s",
            context.message.serialize(as_string=True)
        )

        if not context.connection_ready:
            raise HandlerException("No connection found for keylist update request")

        routing_manager = RouteCoordinationManager(context)

        (
            server_error,
            client_error
        ) = await routing_manager.receive_keylist_update_response()

        if server_error or client_error:
            await responder.send_webhook(
                "keylistupdateresult",
                {
                    "connection_id": context.connection_record.connection_id,
                    "message_id": context.message._id,
                    "content": {
                        "server_error": server_error,
                        "client_error": client_error
                    },
                    "state": "received",
                },
            )
