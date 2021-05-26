"""Presentation message handler."""

from .....ledger.error import LedgerError
from .....messaging.base_handler import BaseHandler
from .....messaging.models.base import BaseModelError
from .....messaging.request_context import RequestContext
from .....messaging.responder import BaseResponder
from .....storage.error import StorageError
from .....utils.tracing import trace_event, get_timer

from .. import problem_report_for_record
from ..manager import PresentationManager
from ..messages.presentation import Presentation
from ..messages.presentation_problem_report import ProblemReportReason


class PresentationHandler(BaseHandler):
    """Message handler class for presentations."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Message handler logic for presentations.

        Args:
            context: request context
            responder: responder callback

        """
        r_time = get_timer()

        self._logger.debug("PresentationHandler called with context %s", context)
        assert isinstance(context.message, Presentation)
        self._logger.info(
            "Received presentation message: %s",
            context.message.serialize(as_string=True),
        )

        presentation_manager = PresentationManager(context.profile)

        presentation_exchange_record = await presentation_manager.receive_presentation(
            context.message, context.connection_record
        )  # mgr saves record state null if need be and possible

        r_time = trace_event(
            context.settings,
            context.message,
            outcome="PresentationHandler.handle.END",
            perf_counter=r_time,
        )

        # Automatically move to next state if flag is set
        if context.settings.get("debug.auto_verify_presentation"):
            try:
                await presentation_manager.verify_presentation(
                    presentation_exchange_record
                )
            except (BaseModelError, LedgerError, StorageError) as err:
                self._logger.exception(err)
                if presentation_exchange_record:
                    async with context.session() as session:
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
                presentation_exchange_record,
                outcome="PresentationHandler.handle.VERIFY",
                perf_counter=r_time,
            )
