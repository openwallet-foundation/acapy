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
from ..manager import CredentialManager, CredentialManagerError
from ..messages.credential_offer import CredentialOffer
from ..messages.credential_problem_report import ProblemReportReason


class CredentialOfferHandler(BaseHandler):
    """Message handler class for credential offers."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Message handler logic for credential offers.

        Args:
            context: request context
            responder: responder callback

        """
        r_time = get_timer()

        self._logger.debug("CredentialOfferHandler called with context %s", context)
        assert isinstance(context.message, CredentialOffer)
        self._logger.info(
            "Received credential offer message: %s",
            context.message.serialize(as_string=True),
        )

        if not context.connection_ready:
            raise HandlerException("No connection established for credential offer")

        credential_manager = CredentialManager(context.profile)
        cred_ex_record = await credential_manager.receive_offer(
            context.message, context.connection_record.connection_id
        )  # mgr only finds, saves record: on exception, saving state null is hopeless

        r_time = trace_event(
            context.settings,
            context.message,
            outcome="CredentialOfferHandler.handle.END",
            perf_counter=r_time,
        )

        # If auto respond is turned on, automatically reply with credential request
        if context.settings.get("debug.auto_respond_credential_offer"):
            credential_request_message = None
            try:
                (
                    _,
                    credential_request_message,
                ) = await credential_manager.create_request(
                    cred_ex_record=cred_ex_record,
                    holder_did=context.connection_record.my_did,
                )
                await responder.send_reply(credential_request_message)
            except (
                BaseModelError,
                CredentialManagerError,
                IndyHolderError,
                LedgerError,
                StorageError,
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
                credential_request_message,
                outcome="CredentialOfferHandler.handle.REQUEST",
                perf_counter=r_time,
            )
