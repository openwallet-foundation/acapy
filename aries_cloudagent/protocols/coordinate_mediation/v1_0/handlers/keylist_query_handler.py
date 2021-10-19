"""Handler for keylist-query message."""

from .....messaging.base_handler import BaseHandler, HandlerException
from .....messaging.request_context import RequestContext
from .....messaging.responder import BaseResponder
from .....storage.error import StorageNotFoundError

from ..manager import MediationManager, MediationNotGrantedError
from ..messages.keylist_query import KeylistQuery
from ..messages.problem_report import CMProblemReport, ProblemReportReason
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

        profile = context.profile
        mgr = MediationManager(profile)
        try:
            async with profile.session() as session:
                record = await MediationRecord.retrieve_by_connection_id(
                    session, context.connection_record.connection_id
                )
            keylist = await mgr.get_keylist(record)
            keylist_response = await mgr.create_keylist_query_response(keylist)
            await responder.send_reply(keylist_response)
        except (StorageNotFoundError, MediationNotGrantedError):
            reply = CMProblemReport(
                description={
                    "en": "Mediation has not been granted for this connection",
                    "code": ProblemReportReason.MEDIATION_NOT_GRANTED.value,
                }
            )
            reply.assign_thread_from(context.message)
            await responder.send_reply(reply)
