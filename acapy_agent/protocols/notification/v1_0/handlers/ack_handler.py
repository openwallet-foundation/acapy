"""Generic ack message handler."""

from .....messaging.base_handler import BaseHandler, HandlerException
from .....messaging.request_context import RequestContext
from .....messaging.responder import BaseResponder
from .....utils.tracing import get_timer, trace_event
from ..messages.ack import V10Ack


class V10AckHandler(BaseHandler):
    """Message handler class for generic acks."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Message handler logic for presentation acks.

        Args:
            context: request context
            responder: responder callback
        """
        r_time = get_timer()

        self._logger.debug(f"V20PresAckHandler called with context {context}")
        assert isinstance(context.message, V10Ack)

        if not context.connection_ready:
            raise HandlerException("No connection established")

        self._logger.info(
            f"Received v1.0 notification ack message: {context.message.serialize(as_string=True)}",
        )

        trace_event(
            context.settings,
            context.message,
            outcome="V10AckHandler.handle.END",
            perf_counter=r_time,
        )
