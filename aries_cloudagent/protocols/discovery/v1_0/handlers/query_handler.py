"""Handler for incoming query messages."""

from .....core.protocol_registry import ProtocolRegistry
from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    RequestContext,
)

from ..messages.disclose import Disclose
from ..messages.query import Query


class QueryHandler(BaseHandler):
    """Handler for incoming query messages."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Message handler implementation."""
        self._logger.debug("QueryHandler called with context %s", context)
        assert isinstance(context.message, Query)

        registry: ProtocolRegistry = context.inject(ProtocolRegistry)
        protocols = registry.protocols_matching_query(context.message.query)
        result = await registry.prepare_disclosed(context, protocols)
        reply = Disclose(protocols=result)
        reply.assign_thread_from(context.message)
        reply.assign_trace_from(context.message)
        await responder.send_reply(reply)
