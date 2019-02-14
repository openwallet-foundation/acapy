"""
The dispatcher is responsible for coordinating data flow between handlers, providing lifecycle
hook callbacks storing state for message threads, etc.
"""

import logging
from typing import Coroutine

from .storage import BaseStorage
from .wallet import BaseWallet, WalletError
from .messaging.agent_message import AgentMessage
from .messaging.request_context import RequestContext
from .messaging.responder import BaseResponder, ResponderError
from .transport.outbound.message import OutboundMessage
from .messaging.message_factory import MessageFactory
from .models.connection_target import ConnectionTarget


class Dispatcher:
    """ """
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def dispatch(
        self,
        context: RequestContext,
        send: Coroutine,
        transport_reply: Coroutine = None,
    ):

        # 1. get handler result
        # 1a. Possibly communicate with service backend for instructions
        # 2. based on some logic, build a response message

        responder = self.make_responder(send, context.wallet, transport_reply)
        handler_cls = context.message.Handler
        handler_response = await handler_cls().handle(context, responder)

        # We return the result to the caller.
        # This is for persistent connections waiting on that response.
        return handler_response

    def make_responder(self, send: Coroutine, wallet: BaseWallet, reply: Coroutine):
        """

        :param send: Coroutine: 
        :param wallet: BaseWallet: 
        :param reply: Coroutine: 

        """
        responder = DispatcherResponder(send, wallet, reply=reply)
        # responder.add_target(ConnectionTarget(endpoint="wss://0bc6628c.ngrok.io"))
        # responder.add_target(ConnectionTarget(endpoint="http://25566605.ngrok.io"))
        responder.add_target(
            ConnectionTarget(endpoint="https://httpbin.org/status/400")
        )
        return responder


class DispatcherResponder(BaseResponder):
    """Handle outgoing messages from message handlers"""

    def __init__(
        self, send: Coroutine, wallet: BaseWallet, *targets, reply: Coroutine = None
    ):
        self._targets = list(targets)
        self._send = send
        self._reply = reply
        self._wallet = wallet

    def add_target(self, target: ConnectionTarget):
        """

        :param target: ConnectionTarget: 

        """
        self._targets.append(target)

    async def send_reply(self, message: AgentMessage):
        if self._reply:
            # 'reply' is a temporary solution to support responses to websocket requests
            # a better solution would likely use a queue to deliver the replies
            await self._reply(message.serialize())
        else:
            if not self._targets:
                raise ResponderError("No active connection")
            for target in self._targets:
                await self.send_outbound(target, message)

    async def send_outbound(self, message: AgentMessage, target: ConnectionTarget):
        await self._send(message, target)

    async def send_admin_message(self, message: AgentMessage):
        pass
