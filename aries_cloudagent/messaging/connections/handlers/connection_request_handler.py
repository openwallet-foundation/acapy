"""Connection request handler."""

from ...base_handler import BaseHandler, BaseResponder, RequestContext

from ..manager import ConnectionManager, ConnectionManagerError
from ..messages.connection_request import ConnectionRequest
from ..messages.problem_report import ProblemReport


class ConnectionRequestHandler(BaseHandler):
    """Handler class for connection requests."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Handle connection request.

        Args:
            context: Request context
            responder: Responder callback
        """

        self._logger.debug(f"ConnectionRequestHandler called with context {context}")
        assert isinstance(context.message, ConnectionRequest)

        mgr = ConnectionManager(context)
        try:
            connection = await mgr.receive_request(
                context.message, context.message_delivery
            )
        except ConnectionManagerError as e:
            self._logger.exception("Error receiving connection request")
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

        if context.settings.get("accept_requests"):
            try:
                response = await mgr.create_response(connection)
            except ConnectionManagerError:
                self._logger.exception("Error creating response to connection request")
                # no return message
                return

            target = await mgr.get_connection_target(connection)
            self._logger.debug("Sending connection response to target: %s", target)
            await responder.send(response, target=target)
        else:
            self._logger.error("Ignoring connection request")
