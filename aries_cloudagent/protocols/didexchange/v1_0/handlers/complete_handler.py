"""Connection complete handler under RFC 23 (DID exchange)."""

from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    RequestContext,
)

from ..manager import Conn23Manager, Conn23ManagerError
from ..messages.response import Conn23Response
from ..messages.problem_report import ProblemReport


class Conn23CompleteHandler(BaseHandler):
    """Handler class for connection complete message under RFC 23 (DID exchange)."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Handle connection complete under RFC 23 (DID exchange).

        Args:
            context: Request context
            responder: Responder callback
        """
        self._logger.debug(f"Conn23CompleteHandler called with context {context}")
        assert isinstance(context.message, Conn23Complete)

        mgr = Conn23Manager(context)
        try:
            conn_rec = await mgr.accept_complete(
                context.message, context.message_receipt
            )
        except Conn23ManagerError as e:
            # no corresponding request: no targets to send problem report; log and quit
            self._logger.exception("Error receiving connection complete")
            return
