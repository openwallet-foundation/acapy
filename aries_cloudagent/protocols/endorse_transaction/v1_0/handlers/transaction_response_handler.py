from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    RequestContext,
)

from ..manager import TransactionManager

class TransactionResponseHandler(BaseHandler):

    async def handle(self, context: RequestContext, responder: BaseResponder):

        mgr = TransactionManager(context)
        await mgr.receive_response(context.message)