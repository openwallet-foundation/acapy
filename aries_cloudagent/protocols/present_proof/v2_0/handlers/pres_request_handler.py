"""Presentation request message handler."""

from .....indy.holder import IndyHolder
from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext,
)
from .....storage.error import StorageNotFoundError
from .....utils.tracing import trace_event, get_timer

from ...indy.pres_preview import IndyPresPreview
from ...indy.xform import indy_proof_req_preview2indy_requested_creds

from ..manager import V20PresManager
from ..messages.pres_format import V20PresFormat
from ..messages.pres_proposal import V20PresProposal
from ..messages.pres_request import V20PresRequest
from ..models.pres_exchange import V20PresExRecord


class V20PresRequestHandler(BaseHandler):
    """Message handler class for v2.0 presentation requests."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Message handler logic for v2.0 presentation requests.

        Args:
            context: request context
            responder: responder callback

        """
        r_time = get_timer()

        self._logger.debug("V20PresRequestHandler called with context %s", context)
        assert isinstance(context.message, V20PresRequest)
        self._logger.info(
            "Received v2.0 presentation request message: %s",
            context.message.serialize(as_string=True),
        )

        if not context.connection_ready:
            raise HandlerException("No connection established for presentation request")

        pres_manager = V20PresManager(context.profile)

        # Get pres ex record (holder initiated via proposal)
        # or create it (verifier sent request first)
        try:
            async with context.session() as session:
                pres_ex_record = await V20PresExRecord.retrieve_by_tag_filter(
                    session,
                    {"thread_id": context.message._thread_id},
                    {"connection_id": context.connection_record.connection_id},
                )  # holder initiated via proposal
        except StorageNotFoundError:  # verifier sent this request free of any proposal
            pres_ex_record = V20PresExRecord(
                conn_id=context.connection_record.connection_id,
                thread_id=context.message._thread_id,
                initiator=V20PresExRecord.INITIATOR_EXTERNAL,
                role=V20PresExRecord.ROLE_PROVER,
                pres_request=context.message.serialize(),
                auto_present=context.settings.get(
                    "debug.auto_respond_presentation_request"
                ),
                trace=(context.message._trace is not None),
            )

        pres_ex_record = await pres_manager.receive_pres_request(pres_ex_record)

        r_time = trace_event(
            context.settings,
            context.message,
            outcome="V20PresRequestHandler.handle.END",
            perf_counter=r_time,
        )

        # If auto_present is enabled, respond immediately with presentation
        if pres_ex_record.auto_present:
            pres_preview = None
            indy_proof_request = context.message.attachment(V20PresFormat.Format.INDY)
            if pres_ex_record.pres_proposal:
                exchange_pres_proposal = V20PresProposal.deserialize(
                    pres_ex_record.pres_proposal
                )
                pres_preview = IndyPresPreview.deserialize(
                    exchange_pres_proposal.attachment(V20PresFormat.Format.INDY)
                )

            try:
                req_creds = await indy_proof_req_preview2indy_requested_creds(
                    indy_proof_request,
                    pres_preview,
                    holder=context.inject(IndyHolder),
                )
            except ValueError as err:
                self._logger.warning(f"{err}")
                return

            (pres_ex_record, pres_message) = await pres_manager.create_pres(
                pres_ex_record=pres_ex_record,
                requested_credentials=req_creds,
                comment=(
                    "auto-presented for proof request nonce "
                    f"{indy_proof_request['nonce']}"
                ),
            )

            await responder.send_reply(pres_message)

            trace_event(
                context.settings,
                pres_message,
                outcome="V20PresRequestHandler.handle.PRESENT",
                perf_counter=r_time,
            )
