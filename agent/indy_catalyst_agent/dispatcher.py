"""
The Dispatcher.

The dispatcher is responsible for coordinating data flow between handlers, providing
lifecycle hook callbacks storing state for message threads, etc.
"""

from asyncio import Future
import logging
from typing import Coroutine, Union

from .messaging.agent_message import AgentMessage
from .messaging.request_context import RequestContext
from .messaging.responder import BaseResponder, ResponderError
from .messaging.connections.models.connection_target import ConnectionTarget
from .wallet.base import BaseWallet


class Dispatcher:
    """
    Dispatcher class.

    Class responsible for dispatching messages to message handlers and responding
    to other agents.
    """

    def __init__(self):
        """Initialize an instance of Dispatcher."""
        self.logger = logging.getLogger(__name__)

    async def dispatch(
        self,
        context: RequestContext,
        send: Coroutine,
        transport_reply: Coroutine = None,
        direct_response: Future = None,
    ):
        """
        Configure responder and dispatch message context to message handler.

        Args:
            context: The `RequestContext` to be handled
            send: Function to send outbound messages
            transport_reply: Function to reply on the incoming channel

        Returns:
            The response from the handler

        """

        try:
            responder = await self.make_responder(
                send, context, transport_reply, direct_response
            )
            handler_cls = context.message.Handler
            handler_response = await handler_cls().handle(context, responder)
        except Exception:
            self.logger.exception("Exception in message handler")
            raise

        # We return the result to the caller.
        # This is for persistent connections waiting on that response.
        return handler_response

    async def make_responder(
        self,
        send: Coroutine,
        context: RequestContext,
        reply: Coroutine,
        direct_response: Future,
    ) -> "DispatcherResponder":
        """
        Build a responder object.

        Args:
            send: Function to send outbound messages
            context: The `RequestContext` to be handled
            reply: Function to reply on the incoming channel

        Returns:
            The created `DispatcherResponder`

        """
        wallet: BaseWallet = await context.inject(BaseWallet)
        responder = DispatcherResponder(
            send, wallet, reply=reply, direct_response=direct_response
        )
        # responder.add_target(ConnectionTarget(endpoint="wss://0bc6628c.ngrok.io"))
        # responder.add_target(ConnectionTarget(endpoint="http://25566605.ngrok.io"))
        # responder.add_target(
        #    ConnectionTarget(endpoint="https://httpbin.org/status/400")
        # )
        if context.connection_target:
            responder.add_target(context.connection_target)
        return responder


class DispatcherResponder(BaseResponder):
    """Handle outgoing messages from message handlers."""

    def __init__(
        self,
        send: Coroutine,
        wallet: BaseWallet,
        *targets,
        reply: Coroutine = None,
        direct_response: Future = None,
    ):
        """
        Initialize an instance of `DispatcherResponder`.

        Args:
            send: Function to send outbound message
            wallet: Wallet instance to use
            targets: List of `ConnectionTarget`s to send to
            reply: Function to reply on incoming channel

        """
        self._direct_response = direct_response
        self._targets = list(targets)
        self._send = send
        self._reply = reply
        self._wallet = wallet

    def add_target(self, target: ConnectionTarget):
        """
        Add target.

        Args:
            target: ConnectionTarget to add
        """
        self._targets.append(target)

    async def send_reply(self, message: Union[AgentMessage, str, bytes]):
        """
        Send a reply to an incoming message.

        Args:
            message: the `AgentMessage`, or pre-packed str or bytes to reply with

        Raises:
            ResponderError: If there is no active connection

        """
        if self._direct_response:
            self._direct_response.set_result(message)
            self._direct_response = None
        elif self._reply:
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
        """
        Send outbound message.

        Args:
            message: `AgentMessage` to send
            target: `ConnectionTarget` to send to
        """
        await self._send(message, target)

    async def send_admin_message(self, message: AgentMessage):
        """Todo."""
        pass
