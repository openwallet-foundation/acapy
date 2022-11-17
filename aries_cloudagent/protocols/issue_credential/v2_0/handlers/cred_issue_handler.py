"""Credential issue message handler."""

from .....core.oob_processor import OobMessageProcessor
from .....indy.holder import IndyHolderError
from .....messaging.base_handler import BaseHandler, HandlerException
from .....messaging.models.base import BaseModelError
from .....messaging.request_context import RequestContext
from .....messaging.responder import BaseResponder
from .....storage.error import StorageError
from .....utils.tracing import trace_event, get_timer

from .. import problem_report_for_record
from ..manager import V20CredManager, V20CredManagerError
from ..messages.cred_issue import V20CredIssue
from ..messages.cred_problem_report import ProblemReportReason


class V20CredIssueHandler(BaseHandler):
    """Message handler class for credential offers."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Message handler logic for credential offers.

        Args:
            context: request context
            responder: responder callback

        """
        r_time = get_timer()

        self._logger.debug("V20CredIssueHandler called with context %s", context)
        assert isinstance(context.message, V20CredIssue)
        self._logger.info(
            "Received v2.0 credential issue message: %s",
            context.message.serialize(as_string=True),
        )

        # If connection is present it must be ready for use
        if context.connection_record and not context.connection_ready:
            raise HandlerException("Connection used for credential not ready")

        # Find associated oob record
        oob_processor = context.inject(OobMessageProcessor)
        oob_record = await oob_processor.find_oob_record_for_inbound_message(context)

        # Either connection or oob context must be present
        if not context.connection_record and not oob_record:
            raise HandlerException(
                "No connection or associated connectionless exchange found for credential"
            )

        cred_manager = V20CredManager(context.profile)
        cred_ex_record = await cred_manager.receive_credential(
            context.message,
            context.connection_record.connection_id
            if context.connection_record
            else None,
        )  # mgr only finds, saves record: on exception, saving null state is hopeless

        r_time = trace_event(
            context.settings,
            context.message,
            outcome="V20CredIssueHandler.handle.END",
            perf_counter=r_time,
        )

        # Automatically move to next state if flag is set
        if context.settings.get("debug.auto_store_credential"):
            try:
                cred_ex_record = await cred_manager.store_credential(cred_ex_record)
            except (
                BaseModelError,
                IndyHolderError,
                StorageError,
                V20CredManagerError,
            ) as err:
                # treat failure to store as mangled on receipt hence protocol error
                self._logger.exception("Error storing issued credential")
                if cred_ex_record:
                    async with context.profile.session() as session:
                        await cred_ex_record.save_error_state(
                            session,
                            reason=err.roll_up,  # us: be specific
                        )
                    await responder.send_reply(
                        problem_report_for_record(
                            cred_ex_record,
                            ProblemReportReason.ISSUANCE_ABANDONED.value,  # them: vague
                        )
                    )

            cred_ack_message = await cred_manager.send_cred_ack(cred_ex_record)

            trace_event(
                context.settings,
                cred_ack_message,
                outcome="V20CredIssueHandler.handle.STORE",
                perf_counter=r_time,
            )
