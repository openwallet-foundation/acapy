"""
The dispatcher is responsible for coordinating data flow between handlers, providing
lifecycle hook callbacks storing state for message threads, etc.
"""

import logging
from typing import Coroutine, Union

from .messaging.agent_message import AgentMessage
from .messaging.request_context import RequestContext
from .messaging.responder import BaseResponder, ResponderError
from .messaging.connections.models.connection_target import ConnectionTarget
from .wallet.base import BaseWallet


class Dispatcher:
    """
    Class responsible for dispatching messages to message handlers and responding
    to other agents.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def dispatch(
        self,
        context: RequestContext,
        send: Coroutine,
        transport_reply: Coroutine = None,
    ):
        """
        Configure responder and dispatch message context to message handler.
        """

        responder = self.make_responder(send, context, transport_reply)
        handler_cls = context.message.Handler
        handler_response = await handler_cls().handle(context, responder)

        # We return the result to the caller.
        # This is for persistent connections waiting on that response.
        return handler_response

    def make_responder(
        self, send: Coroutine, context: RequestContext, reply: Union[Coroutine, None]
    ):
        """
        Build a responder object.
        """
        responder = DispatcherResponder(send, context.wallet, reply=reply)
        # responder.add_target(ConnectionTarget(endpoint="wss://0bc6628c.ngrok.io"))
        # responder.add_target(ConnectionTarget(endpoint="http://25566605.ngrok.io"))
        # responder.add_target(
        #    ConnectionTarget(endpoint="https://httpbin.org/status/400")
        # )
        if context.connection_target:
            responder.add_target(context.connection_target)
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
        Add target.

        :param target: ConnectionTarget: Connection target
        """
        self._targets.append(target)

    async def send_reply(self, message: Union[AgentMessage, str, bytes]):
        if self._reply:
            # 'reply' is a temporary solution to support responses to websocket requests
            # a better solution would likely use a queue to deliver the replies
            await self._reply(message.serialize())
        else:
            if not self._targets:
                raise ResponderError("No active connection")
            for target in self._targets:
                await self.send_outbound(message, target)

    async def send_outbound(
        self, message: Union[AgentMessage, str, bytes], target: ConnectionTarget
    ):
        await self._send(message, target)

    async def send_admin_message(self, message: AgentMessage):
        pass
