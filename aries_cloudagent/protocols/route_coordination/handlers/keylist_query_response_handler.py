"""Keylist query response handler."""


from ....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    RequestContext
)

from ..messages.keylist import KeylistQueryResponse


class KeylistQueryResponseHandler(BaseHandler):
    """Handler for keylist query response."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Message handler logic for keylist query response.

        Args:
            context: request context
            responder: responder callback

        """
        self._logger.debug(
            "KeylistQueryResponseHandler called with context %s",
            context
        )
        assert isinstance(context.message, KeylistQueryResponse)
        self._logger.info(
            "Received keylist update response message: %s",
            context.message.serialize(as_string=True)
        )

        await responder.send_webhook(
            "keylistqueryresult",
            {
                "connection_id": context.connection_record.connection_id,
                "message_id": context.message._id,
                "content": {
                    "keys": context.message.keys,
                    "paginate": context.message.pagination
                },
                "state": "received",
            },
        )
