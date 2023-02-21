"""Presentation message handler."""

from .....core.oob_processor import OobMessageProcessor
from .....ledger.error import LedgerError
from .....messaging.base_handler import BaseHandler, HandlerException
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

        # If connection is present it must be ready for use
        if context.connection_record and not context.connection_ready:
            raise HandlerException("Connection used for presentation not ready")

        # Find associated oob record. If the presentation request was created as an oob
        # attachment the presentation exchange record won't have a connection id (yet)
        oob_processor = context.inject(OobMessageProcessor)
        oob_record = await oob_processor.find_oob_record_for_inbound_message(context)

        # Normally we would do a check here that there is either a connection or
        # an associated oob record. However as present proof supported receiving
        # presentation without oob record or connection record
        # (aip-1 style connectionless) we can't perform this check here

        pres_manager = V20PresManager(context.profile)

        pres_ex_record = await pres_manager.receive_pres(
            context.message, context.connection_record, oob_record
        )

        r_time = trace_event(
            context.settings,
            context.message,
            outcome="V20PresHandler.handle.END",
            perf_counter=r_time,
        )

        # Automatically move to next state if flag is set
        if (
            pres_ex_record
            and pres_ex_record.auto_verify
            or context.settings.get("debug.auto_verify_presentation")
        ):
            try:
                await pres_manager.verify_pres(pres_ex_record, responder)
            except (BaseModelError, LedgerError, StorageError) as err:
                self._logger.exception(err)
                if pres_ex_record:
                    async with context.profile.session() as session:
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
