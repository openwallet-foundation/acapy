"""Credential proposal message handler."""

from .....indy.issuer import IndyIssuerError
from .....ledger.error import LedgerError
from .....messaging.base_handler import BaseHandler, HandlerException
from .....messaging.models.base import BaseModelError
from .....messaging.request_context import RequestContext
from .....messaging.responder import BaseResponder
from .....storage.error import StorageError
from .....utils.tracing import trace_event, get_timer

from .. import problem_report_for_record
from ..manager import V20CredManager, V20CredManagerError
from ..messages.cred_problem_report import ProblemReportReason
from ..messages.cred_proposal import V20CredProposal


class V20CredProposalHandler(BaseHandler):
    """Message handler class for credential proposals."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Message handler logic for credential proposals.

        Args:
            context: proposal context
            responder: responder callback

        """
        r_time = get_timer()

        self._logger.debug("V20CredProposalHandler called with context %s", context)
        assert isinstance(context.message, V20CredProposal)
        self._logger.info(
            "Received v2.0 credential proposal message: %s",
            context.message.serialize(as_string=True),
        )

        # If connection is present it must be ready for use
        if context.connection_record and not context.connection_ready:
            raise HandlerException("Connection used for credential proposal not ready")
        elif not context.connection_record:
            raise HandlerException(
                "Connectionless not supported for credential proposal"
            )

        profile = context.profile
        cred_manager = V20CredManager(profile)
        cred_ex_record = await cred_manager.receive_proposal(
            context.message, context.connection_record.connection_id
        )  # mgr only finds, saves record: on exception, saving state null is hopeless

        r_time = trace_event(
            context.settings,
            context.message,
            outcome="CredentialProposalHandler.handle.END",
            perf_counter=r_time,
        )

        # If auto_offer is enabled, respond immediately with offer
        if cred_ex_record and cred_ex_record.auto_offer:
            cred_offer_message = None
            try:
                (cred_ex_record, cred_offer_message) = await cred_manager.create_offer(
                    cred_ex_record,
                    counter_proposal=None,
                    comment=context.message.comment,
                )
                await responder.send_reply(cred_offer_message)
            except (
                BaseModelError,
                IndyIssuerError,
                LedgerError,
                StorageError,
                V20CredManagerError,
            ) as err:
                self._logger.exception("Error responding to credential proposal")
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

            trace_event(
                context.settings,
                cred_offer_message,
                outcome="V20CredProposalHandler.handle.OFFER",
                perf_counter=r_time,
            )
