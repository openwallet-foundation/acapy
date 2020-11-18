"""Connection response handler under RFC 23 (DID exchange)."""

from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    RequestContext,
)
from .....protocols.trustping.v1_0.messages.ping import Ping

from ..manager import DIDXManager, DIDXManagerError
from ..messages.response import DIDXResponse
from ..messages.problem_report import ProblemReport


class ConnResponseHandler(BaseHandler):
    """Handler class for connection response message under RFC 23 (DID exchange)."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Handle connection response under RFC 23 (DID exchange).

        Args:
            context: Request context
            responder: Responder callback
        """
        self._logger.debug(f"ConnResponseHandler called with context {context}")
        assert isinstance(context.message, ConnResponse)

        mgr = DIDXManager(context)
        try:
            conn_rec = await mgr.accept_response(
                context.message, context.message_receipt
            )
        except DIDXManagerError as e:
            self._logger.exception("Error receiving connection response")
            if e.error_code:
                targets = None
                if context.message.did_doc_attach:
                    try:
                        targets = mgr.diddoc_connection_targets(
                            context.message.did_doc_attach,
                            context.message_receipt.recipient_verkey,
                        )
                    except DIDXManagerError:
                        self._logger.exception(
                            "Error parsing DIDDoc for problem report"
                        )
                await responder.send_reply(
                    ProblemReport(problem_code=e.error_code, explain=str(e)),
                    target_list=targets,
                )
            return

        # send trust ping in response
        if context.settings.get("auto_ping_connection"):
            await responder.send(Ping(), connection_id=conn_rec.connection_id)
