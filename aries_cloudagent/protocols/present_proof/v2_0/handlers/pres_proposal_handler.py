"""Presentation proposal message handler."""

from .....ledger.error import LedgerError
from .....messaging.base_handler import BaseHandler, HandlerException
from .....messaging.models.base import BaseModelError
from .....messaging.request_context import RequestContext
from .....messaging.responder import BaseResponder
from .....storage.error import StorageError
from .....utils.tracing import trace_event, get_timer

from .. import problem_report_for_record
from ..manager import V20PresManager
from ..messages.pres_problem_report import ProblemReportReason
from ..messages.pres_proposal import V20PresProposal


class V20PresProposalHandler(BaseHandler):
    """Message handler class for presentation proposals."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Message handler logic for presentation proposals.

        Args:
            context: proposal context
            responder: responder callback

        """
        r_time = get_timer()

        self._logger.debug("V20PresProposalHandler called with context %s", context)
        assert isinstance(context.message, V20PresProposal)
        self._logger.info(
            "Received v2.0 presentation proposal message: %s",
            context.message.serialize(as_string=True),
        )

        if not context.connection_record:
            raise HandlerException(
                "Connectionless not supported for presentation proposal"
            )
        # If connection is present it must be ready for use
        elif not context.connection_ready:
            raise HandlerException(
                "Connection used for presentation proposal not ready"
            )

        profile = context.profile
        pres_manager = V20PresManager(profile)
        pres_ex_record = await pres_manager.receive_pres_proposal(
            context.message, context.connection_record
        )  # mgr only creates, saves record: on exception, saving state err is hopeless

        r_time = trace_event(
            context.settings,
            context.message,
            outcome="V20PresProposalHandler.handle.END",
            perf_counter=r_time,
        )

        # If auto_respond_presentation_proposal is set, reply with proof req
        if context.settings.get("debug.auto_respond_presentation_proposal"):
            pres_request_message = None
            try:
                (
                    pres_ex_record,
                    pres_request_message,
                ) = await pres_manager.create_bound_request(
                    pres_ex_record=pres_ex_record,
                    comment=context.message.comment,
                )
                await responder.send_reply(pres_request_message)
            except (BaseModelError, LedgerError, StorageError) as err:
                self._logger.exception(err)
                if pres_ex_record:
                    async with profile.session() as session:
                        await pres_ex_record.save_error_state(
                            session,
                            reason=err.roll_up,  # us: be specific
                        )
                    await responder.send_reply(
                        problem_report_for_record(
                            pres_ex_record,
                            ProblemReportReason.ABANDONED.value,  # them: be vague
                        )
                    )

            trace_event(
                context.settings,
                pres_request_message,
                outcome="V20PresProposalHandler.handle.PRESENT",
                perf_counter=r_time,
            )
