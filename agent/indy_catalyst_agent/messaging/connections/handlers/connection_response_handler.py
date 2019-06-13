"""Connection response handler."""

from ...base_handler import BaseHandler, BaseResponder, RequestContext
from ...trustping.messages.ping import Ping

from ..manager import ConnectionManager, ConnectionManagerError
from ..messages.connection_response import ConnectionResponse
from ..messages.problem_report import ProblemReport


class ConnectionResponseHandler(BaseHandler):
    """Handler class for connection responses."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Handle connection response.

        Args:
            context: Request context
            responder: Responder callback
        """
        self._logger.debug(f"ConnectionResponseHandler called with context {context}")
        assert isinstance(context.message, ConnectionResponse)

        mgr = ConnectionManager(context)
        try:
            connection = await mgr.accept_response(
                context.message, context.message_delivery
            )
        except ConnectionManagerError as e:
            self._logger.exception("Error receiving connection response")
            if e.error_code:
                try:
                    target = mgr.diddoc_connection_target(
                        context.message.connection.did_doc,
                        context.message_delivery.recipient_verkey,
                    )
                except ConnectionManagerError:
                    self._logger.exception("Cannot return problem report")
                    return
                await responder.send(
                    ProblemReport(problem_code=e.error_code, explain=str(e)),
                    target=target,
                )
            return

        # send trust ping in response
        if context.settings.get("auto_ping_connection"):
            await responder.send(Ping(), connection_id=connection.connection_id)
