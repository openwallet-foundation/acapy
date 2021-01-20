"""Handshake Reuse Message Handler under RFC 0434."""

from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    RequestContext,
)

from ..manager import OutOfBandManager, OutOfBandManagerError
from ..messages.reuse import HandshakeReuse
from ..messages.problem_report import ProblemReport


class HandshakeReuseMessageHandler(BaseHandler):
    """Handler class for Handshake Reuse Message Handler under RFC 0434."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Handle Handshake Reuse Message Handler under RFC 0434..

        Args:
            context: Request context
            responder: Responder callback
        """
        self._logger.debug(f"HandshakeReuseMessageHandler called with context {context}")
        assert isinstance(context.message, HandshakeReuse)

        session = await context.session()
        mgr = OutOfBandManager(session)
        try:
            await mgr.receive_reuse_message(context.message, context.message_receipt)
        except OutOfBandManagerError as e:
            self._logger.exception("Error processing Handshake Reuse message")
            if e.error_code and e.originating_invi_msg_id and e.originating_reuse_msg_id:
                targets = None
                if context.message.did_doc_attach:
                    try:
                        targets = mgr.diddoc_connection_targets(
                            context.message.did_doc_attach,
                            context.message_receipt.recipient_verkey,
                        )
                    except OutOfBandManagerError:
                        self._logger.exception(
                            "Error parsing DIDDoc for problem report"
                        )
                problem_report = ProblemReport(problem_code=e.error_code, explain=str(e))
                problem_report.assign_thread_id(
                    thid=e.originating_reuse_msg_id,
                    pthid=e.originating_invi_msg_id
                )
                await responder.send_reply(
                    problem_report,
                    target_list=targets,
                )
