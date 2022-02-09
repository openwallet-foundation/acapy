"""Credential offer message handler."""

from .....indy.holder import IndyHolderError
from .....ledger.error import LedgerError
from .....messaging.base_handler import BaseHandler, HandlerException
from .....messaging.models.base import BaseModelError
from .....messaging.request_context import RequestContext
from .....messaging.responder import BaseResponder
from .....storage.error import StorageError
from .....utils.tracing import trace_event, get_timer

from .. import problem_report_for_record
from ..manager import V20CredManager, V20CredManagerError
from ..messages.cred_offer import V20CredOffer
from ..messages.cred_problem_report import ProblemReportReason


class V20CredOfferHandler(BaseHandler):
    """Message handler class for credential offers."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Message handler logic for credential offers.

        Args:
            context: request context
            responder: responder callback

        """
        r_time = get_timer()

        self._logger.debug("V20CredOfferHandler called with context %s", context)
        assert isinstance(context.message, V20CredOffer)
        self._logger.info(
            "Received v2.0 credential offer message: %s",
            context.message.serialize(as_string=True),
        )

        if not context.connection_ready:
            raise HandlerException("No connection established for credential offer")

        cred_manager = V20CredManager(context.profile)
        cred_ex_record = await cred_manager.receive_offer(
            context.message, context.connection_record.connection_id
        )  # mgr only finds, saves record: on exception, saving state null is hopeless

        r_time = trace_event(
            context.settings,
            context.message,
            outcome="V20CredOfferHandler.handle.END",
            perf_counter=r_time,
        )

        # If auto respond is turned on, automatically reply with credential request
        if context.settings.get("debug.auto_respond_credential_offer"):
            cred_request_message = None
            try:
                (_, cred_request_message) = await cred_manager.create_request(
                    cred_ex_record=cred_ex_record,
                    holder_did=context.connection_record.my_did,
                )
                await responder.send_reply(cred_request_message)
            except (
                BaseModelError,
                IndyHolderError,
                LedgerError,
                StorageError,
                V20CredManagerError,
            ) as err:
                self._logger.exception(err)
                if cred_ex_record:
                    async with context.session() as session:
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
                cred_request_message,
                outcome="V20CredOfferHandler.handle.REQUEST",
                perf_counter=r_time,
            )
