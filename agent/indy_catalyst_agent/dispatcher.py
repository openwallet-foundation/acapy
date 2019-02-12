"""
The dispatcher is responsible for coordinating data flow between handlers, providing lifecycle
hook callbacks storing state for message threads, etc.
"""

import logging
from typing import Coroutine

from .storage import BaseStorage
from .wallet import BaseWallet
from .messaging.agent_message import AgentMessage
from .messaging.request_context import RequestContext
from .messaging.responder import BaseResponder, ResponderError
from .transport.outbound.message import OutboundMessage
from .connection import Connection



class Dispatcher:

    def __init__(self, common_context: RequestContext):
        self.logger = logging.getLogger(__name__)
        self.common_context = common_context

    async def dispatch(
            self,
            message: AgentMessage,
            send: Coroutine,
            incoming_transport: str = None,
            transport_reply: Coroutine = None,
        ):
        context = self.common_context.copy()
        context.message = message
        context.transport_type = incoming_transport

        # pack/unpack, set context.sender_verkey, context.recipient_verkey accordingly
        # could choose to set context.default_endpoint and context.default_label
        # based on the recipient verkey used

        # look up existing thread and connection information, if any

        # handle any other decorators having special behaviour (timing, trace, etc)

        # 1. get handler result
        # 1a. Possibly communicate with service backend for instructions
        # 2. based on some logic, build a response message

        responder = self.make_responder(send, transport_reply)
        handler_cls = message.Handler
        handler_response = await handler_cls().handle(context, responder)

        # We return the result to the caller.
        # This is for persistent connections waiting on that response.
        return handler_response

    def make_responder(self, send: Coroutine, reply: Coroutine):
        responder = DispatcherResponder(send, reply=reply)
        #responder.add_target(Connection(endpoint="wss://0bc6628c.ngrok.io"))
        #responder.add_target(Connection(endpoint="http://25566605.ngrok.io"))
        responder.add_target(Connection(endpoint="https://httpbin.org/status/400"))
        return responder


class DispatcherResponder(BaseResponder):
    """
    Handle outgoing messages from message handlers
    """
    def __init__(self, send: Coroutine, *targets, reply: Coroutine = None):
        self._targets = list(targets)
        self._send = send
        self._reply = reply

    def add_target(self, target: Connection):
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

    async def send_outbound(self, connection: Connection, message: AgentMessage):
        await self._send(message, connection)

    async def send_admin_message(self, message: AgentMessage):
        pass
