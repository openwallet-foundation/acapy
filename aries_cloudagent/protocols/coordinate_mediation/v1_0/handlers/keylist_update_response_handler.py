"""Handler for incoming medation grant messages."""

from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext,
)

from ..models.mediation_record import MediationRecord
from ..manager import MediationManager
from ..messages.keylist_update_response import KeylistUpdateResponse
from ..messages.inner.keylist_updated import KeylistUpdated
from ..messages.inner.keylist_update_rule import KeylistUpdateRule
from ....routing.v1_0.models.route_record import RouteRecord
from .....storage.base import StorageNotFoundError


class KeylistUpdateResponseHandler(BaseHandler):
    """Handler for incoming keylist update response messages."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Message handler implementation."""
        self._logger.debug(
            "%s called with context %s", self.__class__.__name__, context
        )
        assert isinstance(context.message, KeylistUpdateResponse)

        if not context.connection_ready:
            raise HandlerException("Invalid mediation request: no active connection")

        for updated in context.message.updated:
            if updated.result != KeylistUpdated.RESULT_SUCCESS:
                continue
            if updated.action == KeylistUpdateRule.RULE_ADD:
                record = RouteRecord(
                    role=RouteRecord.ROLE_CLIENT,
                    recipient_key=updated.recipient_key,
                    connection_id=context.connection_record.connection_id
                )
                await record.save(context, reason="Route successfully added.")
            if updated.action == KeylistUpdateRule.RULE_REMOVE:
                try:
                    records = await RouteRecord.query(
                        context,
                        {
                            'role': RouteRecord.ROLE_CLIENT,
                            'connection_id': context.connection_record.connection_id,
                            'recipient_key': updated.recipient_key
                        }
                    )
                except StorageNotFoundError as err:
                    raise HandlerException('No such route found.') from err

                if len(records) > 1:
                    raise HandlerException('More than one route record found.')

                record = records[0]
                await record.delete_record(context)
