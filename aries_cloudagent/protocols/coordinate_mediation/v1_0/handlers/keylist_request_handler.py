"""Handler for incoming route-list-request messages."""

from .....storage.error import StorageNotFoundError
from ....problem_report.v1_0.message import ProblemReport

from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext,
)

from ..manager import MediationManager as Manager
from ..messages.keylist_query import KeylistQuery as Request
from ..models.mediation_record import MediationRecord as _Record


class KeylistRequestHandler(BaseHandler):
    """Handler for incoming mediation-keylist-request messages."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Message handler implementation."""
        self._logger.debug(
            "%s called with context %s", self.__class__.__name__, context
        )
        assert isinstance(context.message, Request)

        if not context.connection_ready:
            raise HandlerException("Invalid keylist request: no active connection")
        try:
            record = await _Record.retrieve_by_connection_id(
                context, context.connection_record.connection_id
            )
        except StorageNotFoundError:
            await self.reject(responder)
            return

        if record.state == _Record.STATE_GRANTED:
            mgr = Manager(context)
            keylist = await mgr.get_keylist(record)
            keylist_response = mgr.create_keylist_query_response(keylist)
            await responder.send_reply(keylist_response)
        else:
            await self.reject(responder)

    async def reject(self, responder: BaseResponder):
        """Send problem report."""
        await responder.send_reply(
            ProblemReport(
                explain_ltxt="Mediation has not been granted for this connection."
            )
        )
