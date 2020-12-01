"""Handler for incoming medation grant messages."""

from typing import List

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

        to_save: List[RouteRecord] = []
        to_remove: List[RouteRecord] = []
        for updated in context.message.updated:
            if updated.result != KeylistUpdated.RESULT_SUCCESS:
                # TODO better handle different results?
                continue
            if updated.action == KeylistUpdateRule.RULE_ADD:
                record = RouteRecord(
                    role=RouteRecord.ROLE_CLIENT,
                    recipient_key=updated.recipient_key,
                    connection_id=context.connection_record.connection_id
                )
                to_save.append(record)
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
                to_remove.append(record)

        for record_for_saving in to_save:
            await record_for_saving.save(context, reason="Route successfully added.")
        for record_for_removal in to_remove:
            await record_for_removal.delete_record(context)
