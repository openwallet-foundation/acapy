"""Handler for incoming query messages."""

from ...base_handler import BaseHandler, BaseResponder, RequestContext
from ...message_factory import MessageFactory

from ..messages.disclose import Disclose
from ..messages.query import Query


class QueryHandler(BaseHandler):
    """Handler for incoming query messages."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Message handler implementation."""
        self._logger.debug("QueryHandler called with context %s", context)
        assert isinstance(context.message, Query)

        factory: MessageFactory = await context.inject(MessageFactory)
        protocols = factory.protocols_matching_query(context.message.query)
        roles = await factory.determine_roles(context, protocols)
        result = {
            prot: ({"roles": roles[prot]} if prot in roles else {})
            for prot in protocols
        }
        reply = Disclose(protocols=result)
        reply.assign_thread_from(context.message)
        await responder.send_reply(reply)
