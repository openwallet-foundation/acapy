from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    RequestContext,
)

from ..manager import TransactionManager

class TransactionResendHandler(BaseHandler):

    async def handle(self, context: RequestContext, responder: BaseResponder):

        mgr = TransactionManager(context)
        await mgr.receive_transaction_resend(context.message)