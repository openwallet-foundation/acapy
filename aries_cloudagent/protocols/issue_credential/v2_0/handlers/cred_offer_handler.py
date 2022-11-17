"""Credential offer message handler."""

from .....wallet.util import default_did_from_verkey
from .....core.oob_processor import OobMessageProcessor
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

        # If connection is present it must be ready for use
        if context.connection_record and not context.connection_ready:
            raise HandlerException("Connection used for credential offer not ready")

        # Find associated oob record
        oob_processor = context.inject(OobMessageProcessor)
        oob_record = await oob_processor.find_oob_record_for_inbound_message(context)

        # Either connection or oob context must be present
        if not context.connection_record and not oob_record:
            raise HandlerException(
                "No connection or associated connectionless exchange found for credential"
                " offer"
            )

        connection_id = (
            context.connection_record.connection_id
            if context.connection_record
            else None
        )

        profile = context.profile
        cred_manager = V20CredManager(profile)
        cred_ex_record = await cred_manager.receive_offer(
            context.message, connection_id
        )  # mgr only finds, saves record: on exception, saving state null is hopeless

        r_time = trace_event(
            context.settings,
            context.message,
            outcome="V20CredOfferHandler.handle.END",
            perf_counter=r_time,
        )

        if context.connection_record:
            holder_did = context.connection_record.my_did
        else:
            # Transform recipient key into did
            holder_did = default_did_from_verkey(oob_record.our_recipient_key)

        # If auto respond is turned on, automatically reply with credential request
        if context.settings.get("debug.auto_respond_credential_offer"):
            cred_request_message = None
            try:
                (_, cred_request_message) = await cred_manager.create_request(
                    cred_ex_record=cred_ex_record,
                    holder_did=holder_did,
                )
                await responder.send_reply(cred_request_message)
            except (
                BaseModelError,
                IndyHolderError,
                LedgerError,
                StorageError,
                V20CredManagerError,
            ) as err:
                self._logger.exception("Error responding to credential offer")
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

            trace_event(
                context.settings,
                cred_request_message,
                outcome="V20CredOfferHandler.handle.REQUEST",
                perf_counter=r_time,
            )
