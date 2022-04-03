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
from ..manager import CredentialManager, CredentialManagerError
from ..messages.credential_issue import CredentialIssue
from ..messages.credential_problem_report import ProblemReportReason


class CredentialIssueHandler(BaseHandler):
    """Message handler class for credential offers."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Message handler logic for credential offers.

        Args:
            context: request context
            responder: responder callback

        """
        r_time = get_timer()
        profile = context.profile
        self._logger.debug("CredentialHandler called with context %s", context)
        assert isinstance(context.message, CredentialIssue)
        self._logger.info(
            "Received credential message: %s", context.message.serialize(as_string=True)
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

        credential_manager = CredentialManager(profile)
        cred_ex_record = await credential_manager.receive_credential(
            context.message,
            context.connection_record.connection_id
            if context.connection_record
            else None,
        )  # mgr only finds, saves record: on exception, saving state null is hopeless

        r_time = trace_event(
            context.settings,
            context.message,
            outcome="CredentialIssueHandler.handle.END",
            perf_counter=r_time,
        )

        # Automatically move to next state if flag is set
        if cred_ex_record and context.settings.get("debug.auto_store_credential"):
            try:
                cred_ex_record = await credential_manager.store_credential(
                    cred_ex_record
                )
            except (
                BaseModelError,
                CredentialManagerError,
                IndyHolderError,
                StorageError,
            ) as err:
                # treat failure to store as mangled on receipt hence protocol error
                self._logger.exception("Error storing issued credential")
                if cred_ex_record:
                    async with profile.session() as session:
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

            (_, credential_ack_message) = await credential_manager.send_credential_ack(
                cred_ex_record
            )

            trace_event(
                context.settings,
                credential_ack_message,
                outcome="CredentialIssueHandler.handle.STORE",
                perf_counter=r_time,
            )
