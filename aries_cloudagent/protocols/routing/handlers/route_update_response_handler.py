"""Handler for incoming route-update-response messages."""

from ....connections.models.connection_record import ConnectionRecord
from ....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext,
)

from ...connections.manager import ConnectionManager

from ..messages.route_update_response import RouteUpdateResponse
from ..models.route_update import RouteUpdate
from ..models.route_updated import RouteUpdated


class RouteUpdateResponseHandler(BaseHandler):
    """Handler for incoming route-update-response messages."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Message handler implementation."""
        self._logger.debug(
            "%s called with context %s", self.__class__.__name__, context
        )
        assert isinstance(context.message, RouteUpdateResponse)

        if not context.connection_ready:
            raise HandlerException("Cannot handle updated routes: no active connection")

        conn_mgr = ConnectionManager(context)
        router_id = context.connection_record.connection_id

        for update in context.message.updated:
            if update.action == RouteUpdate.ACTION_CREATE:
                if update.result in (
                    RouteUpdated.RESULT_NO_CHANGE,
                    RouteUpdated.RESULT_SUCCESS,
                ):
                    routing_state = ConnectionRecord.ROUTING_STATE_ACTIVE
                else:
                    routing_state = ConnectionRecord.ROUTING_STATE_ERROR
                    self._logger.warning(
                        f"Unexpected result from inbound route update ({update.action})"
                    )
                await conn_mgr.update_inbound(
                    router_id, update.recipient_key, routing_state
                )
            elif update.action == RouteUpdate.ACTION_DELETE:
                self._logger.info(
                    "Inbound route deletion status: {}, {}".format(
                        update.recipient_key, update.result
                    )
                )
            else:
                self._logger.error(f"Unsupported inbound route action: {update.action}")
