"""Credential request message handler."""

from .....core.oob_processor import OobMessageProcessor
from .....indy.issuer import IndyIssuerError
from .....ledger.error import LedgerError
from .....messaging.base_handler import BaseHandler, HandlerException
from .....messaging.models.base import BaseModelError
from .....messaging.request_context import RequestContext
from .....messaging.responder import BaseResponder
from .....storage.error import StorageError
from .....utils.tracing import trace_event, get_timer

from .. import problem_report_for_record
from ..manager import CredentialManager, CredentialManagerError
from ..messages.credential_problem_report import ProblemReportReason
from ..messages.credential_request import CredentialRequest


class CredentialRequestHandler(BaseHandler):
    """Message handler class for credential requests."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Message handler logic for credential requests.

        Args:
            context: request context
            responder: responder callback

        """
        r_time = get_timer()
        profile = context.profile
        self._logger.debug("CredentialRequestHandler called with context %s", context)
        assert isinstance(context.message, CredentialRequest)
        self._logger.info(
            "Received credential request message: %s",
            context.message.serialize(as_string=True),
        )

        # If connection is present it must be ready for use
        if context.connection_record and not context.connection_ready:
            raise HandlerException("Connection used for credential request not ready")

        # Find associated oob record. If the credential offer was created as an oob
        # attachment the presentation exchange record won't have a connection id (yet)
        oob_processor = context.inject(OobMessageProcessor)
        oob_record = await oob_processor.find_oob_record_for_inbound_message(context)

        # Either connection or oob context must be present
        if not context.connection_record and not oob_record:
            raise HandlerException(
                "No connection or associated connectionless exchange found for credential"
                " request"
            )

        credential_manager = CredentialManager(profile)
        cred_ex_record = await credential_manager.receive_request(
            context.message, context.connection_record, oob_record
        )  # mgr only finds, saves record: on exception, saving state null is hopeless

        r_time = trace_event(
            context.settings,
            context.message,
            outcome="CredentialRequestHandler.handle.END",
            perf_counter=r_time,
        )

        # If auto_issue is enabled, respond immediately
        if cred_ex_record and cred_ex_record.auto_issue:
            if (
                cred_ex_record.credential_proposal_dict
                and cred_ex_record.credential_proposal_dict.credential_proposal
            ):
                credential_issue_message = None
                try:
                    (
                        cred_ex_record,
                        credential_issue_message,
                    ) = await credential_manager.issue_credential(
                        cred_ex_record=cred_ex_record,
                        comment=context.message.comment,
                    )
                    await responder.send_reply(credential_issue_message)
                except (
                    BaseModelError,
                    CredentialManagerError,
                    IndyIssuerError,
                    LedgerError,
                    StorageError,
                ) as err:
                    self._logger.exception("Error responding to credential request")
                    if cred_ex_record:
                        async with profile.session() as session:
                            await cred_ex_record.save_error_state(
                                session,
                                reason=err.roll_up,  # us: be specific
                            )
                        await responder.send_reply(  # them: be vague
                            problem_report_for_record(
                                cred_ex_record,
                                ProblemReportReason.ISSUANCE_ABANDONED.value,
                            )
                        )

                trace_event(
                    context.settings,
                    credential_issue_message,
                    outcome="CredentialRequestHandler.issue.END",
                    perf_counter=r_time,
                )
            else:
                self._logger.warning(
                    "Operation set for auto-issue but credential exchange record "
                    f"{cred_ex_record.credential_exchange_id} "
                    "has no attribute values"
                )
