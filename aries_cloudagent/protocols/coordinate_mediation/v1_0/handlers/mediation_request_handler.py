"""Handler for mediate-request message."""

from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext,
)
from ....problem_report.v1_0.message import ProblemReport
from ..manager import MediationManager, MediationAlreadyExists
from ..messages.mediate_request import MediationRequest


class MediationRequestHandler(BaseHandler):
    """Handler for mediate-request message."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Handle mediate-request message."""
        self._logger.debug(
            "%s called with context %s", self.__class__.__name__, context
        )
        assert isinstance(context.message, MediationRequest)

        if not context.connection_ready:
            raise HandlerException("Invalid mediation request: no active connection")

        mgr = MediationManager(context.profile)
        try:
            record = await mgr.receive_request(
                context.connection_record.connection_id, context.message
            )
            if context.settings.get("mediation.open", False):
                record, grant = await mgr.grant_request(record.mediation_id)
                await responder.send_reply(grant)
        except MediationAlreadyExists:
            await responder.send_reply(
                ProblemReport(
                    explain_ltxt="Mediation request already exists from this connection."
                )
            )
