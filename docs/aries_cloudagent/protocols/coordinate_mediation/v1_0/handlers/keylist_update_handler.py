"""Handler for keylist-update messages."""

from .....messaging.base_handler import BaseHandler, HandlerException
from .....messaging.request_context import RequestContext
from .....messaging.responder import BaseResponder
from .....storage.error import StorageNotFoundError

from ..manager import MediationManager, MediationNotGrantedError
from ..messages.keylist_update import KeylistUpdate
from ..messages.problem_report import CMProblemReport, ProblemReportReason
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

        profile = context.profile
        mgr = MediationManager(profile)
        try:
            async with profile.session() as session:
                record = await MediationRecord.retrieve_by_connection_id(
                    session, context.connection_record.connection_id
                )
            response = await mgr.update_keylist(record, updates=context.message.updates)
            response.assign_thread_from(context.message)
            await responder.send_reply(response)
        except (StorageNotFoundError, MediationNotGrantedError):
            reply = CMProblemReport(
                description={
                    "en": "Mediation has not been granted for this connection",
                    "code": ProblemReportReason.MEDIATION_NOT_GRANTED.value,
                }
            )
            reply.assign_thread_from(context.message)
            await responder.send_reply(reply)
