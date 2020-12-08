"""Handler for keylist-update messages."""

from .....messaging.base_handler import (
    BaseHandler, BaseResponder, HandlerException, RequestContext
)
from .....storage.error import StorageNotFoundError
from ....problem_report.v1_0.message import ProblemReport
from ..manager import MediationManager, MediationNotGrantedError
from ..messages.keylist_update import KeylistUpdate
from ..models.mediation_record import MediationRecord


class KeylistUpdateHandler(BaseHandler):
    """Handler for keylist-update messages."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Handle keylist-update messages."""
        self._logger.debug(
            "%s called with context %s", self.__class__.__name__, context
        )
        assert isinstance(context.message, KeylistUpdate)

        if not context.connection_ready:
            raise HandlerException("Cannot update routes: no active connection")

        session = await context.session()
        try:
            record = await MediationRecord.retrieve_by_connection_id(
                session, context.connection_record.connection_id
            )
        except StorageNotFoundError:
            await self.reject(responder)
            return

        mgr = MediationManager(session)
        try:
            response = await mgr.update_keylist(
                record, updates=context.message.updates
            )
            await responder.send_reply(response)
        except MediationNotGrantedError:
            await self.reject(responder)

    async def reject(self, responder: BaseResponder):
        """Send problem report."""
        await responder.send_reply(
            ProblemReport(
                explain_ltxt="Mediation has not been granted for this connection."
            )
        )
