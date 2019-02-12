import logging

from ...base_handler import BaseHandler
from ...request_context import RequestContext
from ...responder import BaseResponder

# from ..messages.connection_invitation import ConnectionInvitation


class ConnectionInvitationHandler(BaseHandler):
    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)

    async def handle(self, context: RequestContext, responder: BaseResponder):
        self.logger.debug(
            f"ConnectionInvitationHandler called with context {context}"
        )
        #await responder.send_reply(context.message)
        #return context.message
