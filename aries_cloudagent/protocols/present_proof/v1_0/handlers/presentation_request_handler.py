"""Presentation request message handler."""

from .....indy.holder import IndyHolder, IndyHolderError
from .....indy.sdk.models.xform import indy_proof_req_preview2indy_requested_creds
from .....ledger.error import LedgerError
from .....messaging.base_handler import BaseHandler, HandlerException
from .....messaging.request_context import RequestContext
from .....messaging.responder import BaseResponder
from .....storage.error import StorageError, StorageNotFoundError
from .....utils.tracing import trace_event, get_timer
from .....wallet.error import WalletNotFoundError

from ..manager import PresentationManager, PresentationManagerError
from ..messages.presentation_proposal import PresentationProposal
from ..messages.presentation_request import PresentationRequest
from ..models.presentation_exchange import V10PresentationExchange


class PresentationRequestHandler(BaseHandler):
    """Message handler class for Aries#0037 v1.0 presentation requests."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Message handler logic for Aries#0037 v1.0 presentation requests.

        Args:
            context: request context
            responder: responder callback

        """
        r_time = get_timer()

        self._logger.debug("PresentationRequestHandler called with context %s", context)
        assert isinstance(context.message, PresentationRequest)
        self._logger.info(
            "Received presentation request message: %s",
            context.message.serialize(as_string=True),
        )

        if not context.connection_ready:
            raise HandlerException("No connection established for presentation request")

        presentation_manager = PresentationManager(context.profile)

        indy_proof_request = context.message.indy_proof_request(0)

        # Get presentation exchange record (holder initiated via proposal)
        # or create it (verifier sent request first)
        try:
            async with context.session() as session:
                (
                    presentation_exchange_record
                ) = await V10PresentationExchange.retrieve_by_tag_filter(
                    session,
                    {"thread_id": context.message._thread_id},
                    {"connection_id": context.connection_record.connection_id},
                )  # holder initiated via proposal
        except StorageNotFoundError:  # verifier sent this request free of any proposal
            presentation_exchange_record = V10PresentationExchange(
                connection_id=context.connection_record.connection_id,
                thread_id=context.message._thread_id,
                initiator=V10PresentationExchange.INITIATOR_EXTERNAL,
                role=V10PresentationExchange.ROLE_PROVER,
                presentation_request=indy_proof_request,
                presentation_request_dict=context.message.serialize(),
                auto_present=context.settings.get(
                    "debug.auto_respond_presentation_request"
                ),
                trace=(context.message._trace is not None),
            )

        presentation_exchange_record.presentation_request = indy_proof_request
        presentation_exchange_record = await presentation_manager.receive_request(
            presentation_exchange_record
        )  # mgr only saves record: on exception, saving state null is hopeless

        r_time = trace_event(
            context.settings,
            context.message,
            outcome="PresentationRequestHandler.handle.END",
            perf_counter=r_time,
        )

        # If auto_present is enabled, respond immediately with presentation
        if presentation_exchange_record.auto_present:
            presentation_preview = None
            if presentation_exchange_record.presentation_proposal_dict:
                exchange_pres_proposal = PresentationProposal.deserialize(
                    presentation_exchange_record.presentation_proposal_dict
                )
                presentation_preview = exchange_pres_proposal.presentation_proposal

            try:
                req_creds = await indy_proof_req_preview2indy_requested_creds(
                    indy_proof_request,
                    presentation_preview,
                    holder=context.inject(IndyHolder),
                )
            except ValueError as err:
                self._logger.warning(f"{err}")
                return

            presentation_message = None
            try:
                (
                    presentation_exchange_record,
                    presentation_message,
                ) = await presentation_manager.create_presentation(
                    presentation_exchange_record=presentation_exchange_record,
                    requested_credentials=req_creds,
                    comment="auto-presented for proof request nonce={}".format(
                        indy_proof_request["nonce"]
                    ),
                )
                await responder.send_reply(presentation_message)
            except (
                IndyHolderError,
                LedgerError,
                PresentationManagerError,
                WalletNotFoundError,
            ) as err:
                self._logger.exception(err)
                if presentation_exchange_record:
                    await presentation_exchange_record.save_error_state(
                        context.session(),
                        reason=err.message,
                    )
            except StorageError as err:
                self._logger.exception(err)  # may be logging to wire, not dead disk

            trace_event(
                context.settings,
                presentation_message,
                outcome="PresentationRequestHandler.handle.PRESENT",
                perf_counter=r_time,
            )
