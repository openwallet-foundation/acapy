"""Presentation proposal message handler."""

from .....ledger.error import LedgerError
from .....messaging.base_handler import BaseHandler, HandlerException
from .....messaging.models.base import BaseModelError
from .....messaging.request_context import RequestContext
from .....messaging.responder import BaseResponder
from .....storage.error import StorageError
from .....utils.tracing import trace_event, get_timer

from .. import problem_report_for_record
from ..manager import PresentationManager
from ..messages.presentation_problem_report import ProblemReportReason
from ..messages.presentation_proposal import PresentationProposal


class PresentationProposalHandler(BaseHandler):
    """Message handler class for presentation proposals."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Message handler logic for presentation proposals.

        Args:
            context: proposal context
            responder: responder callback

        """
        r_time = get_timer()
        profile = context.profile
        self._logger.debug(
            "PresentationProposalHandler called with context %s", context
        )
        assert isinstance(context.message, PresentationProposal)
        self._logger.info(
            "Received presentation proposal message: %s",
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

        presentation_manager = PresentationManager(profile)
        presentation_exchange_record = await presentation_manager.receive_proposal(
            context.message, context.connection_record
        )  # mgr only creates, saves record: on exception, saving state null is hopeless

        r_time = trace_event(
            context.settings,
            context.message,
            outcome="PresentationProposalHandler.handle.END",
            perf_counter=r_time,
        )

        # If auto_respond_presentation_proposal is set, reply with proof req
        if context.settings.get("debug.auto_respond_presentation_proposal"):
            presentation_request_message = None
            try:
                (
                    presentation_exchange_record,
                    presentation_request_message,
                ) = await presentation_manager.create_bound_request(
                    presentation_exchange_record=presentation_exchange_record,
                    comment=context.message.comment,
                )
                await responder.send_reply(presentation_request_message)
            except (BaseModelError, LedgerError, StorageError) as err:
                self._logger.exception(err)
                if presentation_exchange_record:
                    async with profile.session() as session:
                        await presentation_exchange_record.save_error_state(
                            session,
                            reason=err.roll_up,  # us: be specific
                        )
                    await responder.send_reply(
                        problem_report_for_record(
                            presentation_exchange_record,
                            ProblemReportReason.ABANDONED.value,  # them: be vague
                        )
                    )

            trace_event(
                context.settings,
                presentation_request_message,
                outcome="PresentationProposalHandler.handle.PRESENT",
                perf_counter=r_time,
            )
