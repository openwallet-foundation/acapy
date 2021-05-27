"""Presentation message handler."""

from .....ledger.error import LedgerError
from .....messaging.base_handler import BaseHandler
from .....messaging.models.base import BaseModelError
from .....messaging.request_context import RequestContext
from .....messaging.responder import BaseResponder
from .....storage.error import StorageError
from .....utils.tracing import trace_event, get_timer

from .. import problem_report_for_record
from ..manager import V20PresManager
from ..messages.pres import V20Pres
from ..messages.pres_problem_report import ProblemReportReason


class V20PresHandler(BaseHandler):
    """Message handler class for presentations."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Message handler logic for presentations.

        Args:
            context: request context
            responder: responder callback

        """
        r_time = get_timer()

        self._logger.debug("V20PresHandler called with context %s", context)
        assert isinstance(context.message, V20Pres)
        self._logger.info(
            "Received presentation message: %s",
            context.message.serialize(as_string=True),
        )

        pres_manager = V20PresManager(context.profile)

        pres_ex_record = await pres_manager.receive_pres(
            context.message, context.connection_record
        )

        r_time = trace_event(
            context.settings,
            context.message,
            outcome="V20PresHandler.handle.END",
            perf_counter=r_time,
        )

        # Automatically move to next state if flag is set
        if context.settings.get("debug.auto_verify_presentation"):
            try:
                await pres_manager.verify_pres(pres_ex_record)
            except (BaseModelError, LedgerError, StorageError) as err:
                self._logger.exception(err)
                if pres_ex_record:
                    async with context.session() as session:
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
                pres_ex_record,
                outcome="V20PresHandler.handle.VERIFY",
                perf_counter=r_time,
            )
