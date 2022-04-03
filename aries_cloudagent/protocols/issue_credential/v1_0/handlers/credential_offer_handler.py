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
        profile = context.profile
        self._logger.debug("CredentialOfferHandler called with context %s", context)
        assert isinstance(context.message, CredentialOffer)
        self._logger.info(
            "Received credential offer message: %s",
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

        credential_manager = CredentialManager(profile)
        cred_ex_record = await credential_manager.receive_offer(
            context.message, connection_id
        )  # mgr only finds, saves record: on exception, saving state null is hopeless

        r_time = trace_event(
            context.settings,
            context.message,
            outcome="CredentialOfferHandler.handle.END",
            perf_counter=r_time,
        )

        if context.connection_record:
            holder_did = context.connection_record.my_did
        else:
            # Transform recipient key into did
            holder_did = default_did_from_verkey(oob_record.our_recipient_key)

        # If auto respond is turned on, automatically reply with credential request
        if cred_ex_record and context.settings.get(
            "debug.auto_respond_credential_offer"
        ):
            credential_request_message = None
            try:
                (
                    _,
                    credential_request_message,
                ) = await credential_manager.create_request(
                    cred_ex_record=cred_ex_record,
                    holder_did=holder_did,
                )
                await responder.send_reply(credential_request_message)
            except (
                BaseModelError,
                CredentialManagerError,
                IndyHolderError,
                LedgerError,
                StorageError,
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
                credential_request_message,
                outcome="CredentialOfferHandler.handle.REQUEST",
                perf_counter=r_time,
            )
