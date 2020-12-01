"""Handler for keylist-query message."""

from .....messaging.base_handler import (
    BaseHandler, BaseResponder, HandlerException, RequestContext
)
from .....storage.error import StorageNotFoundError
from ....problem_report.v1_0.message import ProblemReport
from ..manager import MediationManager as Manager
from ..messages.keylist_query import KeylistQuery
from ..models.mediation_record import MediationRecord


class KeylistQueryHandler(BaseHandler):
    """Handler for keylist-query message."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Handle keylist-query message."""
        self._logger.debug(
            "%s called with context %s", self.__class__.__name__, context
        )
        assert isinstance(context.message, KeylistQuery)

        if not context.connection_ready:
            raise HandlerException("Invalid keylist query: no active connection")

        try:
            record = await MediationRecord.retrieve_by_connection_id(
                context, context.connection_record.connection_id
            )
        except StorageNotFoundError:
            await self.reject(responder)
            return

        if record.state != MediationRecord.STATE_GRANTED:
            await self.reject(responder)
            return

        mgr = Manager(context)
        keylist = await mgr.get_keylist(record)
        keylist_response = mgr.create_keylist_query_response(keylist)
        await responder.send_reply(keylist_response)

    async def reject(self, responder: BaseResponder):
        """Send problem report."""
        await responder.send_reply(
            ProblemReport(
                explain_ltxt="Mediation has not been granted for this connection."
            )
        )
