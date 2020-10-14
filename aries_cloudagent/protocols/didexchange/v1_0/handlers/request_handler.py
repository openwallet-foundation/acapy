"""Connection request handler under RFC 23 (DID exchange)."""

from .....messaging.base_handler import BaseHandler, BaseResponder, RequestContext

from ..manager import Conn23Manager, Conn23ManagerError
from ..messages.request import Conn23Request
from ..messages.problem_report import ProblemReport


class Conn23RequestHandler(BaseHandler):
    """Handler class for connection request message under RFC 23 (DID exchange)."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Handle connection request under RFC 23 (DID exchange).

        Args:
            context: Request context
            responder: Responder callback
        """

        self._logger.debug(f"Conn23RequestHandler called with context {context}")
        assert isinstance(context.message, Conn23Request)

        mgr = Conn23Manager(context)
        try:
            await mgr.receive_request(context.message, context.message_receipt)
        except Conn23ManagerError as e:
            self._logger.exception("Error receiving RFC 23 connection request")
            if e.error_code:
                targets = None
                if context.message.did_doc_attach:
                    try:
                        targets = mgr.diddoc_connection_targets(
                            context.message.did_doc_attach,
                            context.message_receipt.recipient_verkey,
                        )
                    except Conn23ManagerError:
                        self._logger.exception(
                            "Error parsing DIDDoc for problem report"
                        )
                await responder.send_reply(
                    ProblemReport(problem_code=e.error_code, explain=str(e)),
                    target_list=targets,
                )
