"""
The Dispatcher.

The dispatcher is responsible for coordinating data flow between handlers, providing
lifecycle hook callbacks storing state for message threads, etc.
"""

import asyncio
import logging
from typing import Coroutine, Union

from .messaging.agent_message import AgentMessage
from .messaging.connections.manager import ConnectionManager
from .messaging.error import MessageParseError
from .messaging.message_delivery import MessageDelivery
from .messaging.message_factory import MessageFactory
from .messaging.problem_report.message import ProblemReport
from .messaging.request_context import RequestContext
from .messaging.responder import BaseResponder, ResponderError
from .messaging.serializer import MessageSerializer
from .messaging.connections.models.connection_target import ConnectionTarget
from .models.base import BaseModelError


class Dispatcher:
    """
    Dispatcher class.

    Class responsible for dispatching messages to message handlers and responding
    to other agents.
    """

    def __init__(self, context: RequestContext):
        """Initialize an instance of Dispatcher."""
        self.context = context
        self.logger = logging.getLogger(__name__)

    async def dispatch(
        self,
        parsed_msg: dict,
        delivery: MessageDelivery,
        send: Coroutine,
        transport_reply: Coroutine = None,
        allow_direct_response: bool = False,
    ) -> AgentMessage:
        """
        Configure responder and dispatch message context to message handler.

        Args:
            parsed_msg:
            delivery:
            send: Function to send outbound messages
            transport_reply: Function to reply on the incoming channel
            allow_direct_response:

        Returns:
            The response from the handler

        """

        try:
            message = await self.make_message(parsed_msg)
        except MessageParseError as e:
            return ProblemReport(explain_ltxt=str(e))

        context = self.context.start_scope("message")
        context.message = message
        context.message_delivery = delivery

        connection_mgr = ConnectionManager(context)

        # updates delivery.direct_response_requested and potentially updates connection
        connection = await connection_mgr.find_message_connection(delivery)

        if delivery.direct_response_requested == "all":
            if allow_direct_response:
                delivery.direct_response = True
            else:
                self.logger.warning(
                    "Direct response requested, but not supported by transport: %s",
                    delivery.transport_type,
                )

        context.connection_active = connection and connection.is_active
        context.connection_record = connection
        if connection:
            context.connection_target = await self.connection_mgr.get_connection_target(
                connection
            )

        direct_response = delivery.direct_response and asyncio.Future() or None

        try:
            responder = await self.make_responder(
                send, context, transport_reply, direct_response
            )
            handler_cls = context.message.Handler
            handler = asyncio.ensure_future(handler_cls().handle(context, responder))

            if direct_response:
                # wait for either a direct response or the end of the handler
                await asyncio.wait(
                    [direct_response, handler], return_when=asyncio.FIRST_COMPLETED
                )
            else:
                await handler
        except Exception:
            self.logger.exception("Exception in message handler")
            raise

        # We return the result to the caller.
        # This is for persistent connections waiting on that response.
        if direct_response and direct_response.done():
            return direct_response.result()

    async def make_message(self, parsed_msg: dict) -> AgentMessage:
        """
        Deserialize a message dict into the appropriate message instance.

        Given a dict describing a message, this method
        returns an instance of the related message class.

        Args:
            parsed_msg: The parsed message

        Returns:
            An instance of the corresponding message class for this message

        Raises:
            MessageParseError: If the message doesn't specify @type
            MessageParseError: If there is no message class registered to handle
                the given type

        """

        factory: MessageFactory = await self.context.inject(MessageFactory)
        serializer: MessageSerializer = await self.context.inject(MessageSerializer)

        # throws a MessageParseError on failure
        message_type = serializer.extract_message_type(parsed_msg)

        message_cls = factory.resolve_message_class(message_type)

        if not message_cls:
            raise MessageParseError(f"Unrecognized message type {message_type}")

        try:
            instance = message_cls.deserialize(parsed_msg)
        except BaseModelError as e:
            raise MessageParseError(f"Error deserializing message: {e}") from e

        return instance

    async def make_responder(
        self,
        send: Coroutine,
        context: RequestContext,
        reply: Coroutine,
        direct_response: asyncio.Future,
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
        responder = DispatcherResponder(
            send, context, reply=reply, direct_response=direct_response
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
        context: RequestContext,
        *targets,
        reply: Coroutine = None,
        direct_response: asyncio.Future = None,
    ):
        """
        Initialize an instance of `DispatcherResponder`.

        Args:
            send: Function to send outbound message
            wallet: Wallet instance to use
            targets: List of `ConnectionTarget`s to send to
            reply: Function to reply on incoming channel

        """
        self._context = context
        self._direct_response = direct_response
        self._targets = list(targets)
        self._send = send
        self._reply = reply

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
        await self._send(self._context, message, target)

    async def send_admin_message(self, message: AgentMessage):
        """Todo."""
        pass
