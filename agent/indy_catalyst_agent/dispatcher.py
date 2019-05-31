"""
The Dispatcher.

The dispatcher is responsible for coordinating data flow between handlers, providing
lifecycle hook callbacks storing state for message threads, etc.
"""

import asyncio
import logging
from typing import Coroutine, Union

from .messaging.agent_message import AgentMessage
from .messaging.connections.models.connection_record import ConnectionRecord
from .messaging.error import MessageParseError
from .messaging.message_delivery import MessageDelivery
from .messaging.message_factory import MessageFactory
from .messaging.outbound_message import OutboundMessage
from .messaging.problem_report.message import ProblemReport
from .messaging.request_context import RequestContext
from .messaging.responder import BaseResponder
from .messaging.serializer import MessageSerializer
from .messaging.util import datetime_now
from .models.timing_decorator import TimingDecorator
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
        connection: ConnectionRecord,
        send: Coroutine,
    ) -> asyncio.Future:
        """
        Configure responder and dispatch message context to message handler.

        Args:
            parsed_msg: The parsed message body
            delivery: The incoming message delivery metadata
            connection: The related connection record, if any
            send: Function to send outbound messages

        Returns:
            The response from the handler

        """

        error_result = None
        try:
            message = await self.make_message(parsed_msg)
        except MessageParseError as e:
            self.logger.error(
                f"Message parsing failed: {str(e)}, sending problem report"
            )
            error_result = ProblemReport(explain_ltxt=str(e))
            if delivery.thread_id:
                error_result.assign_thread_id(delivery.thread_id)
            message = None

        context = self.context.start_scope("message")
        context.message = message
        context.message_delivery = delivery
        context.connection_active = connection and connection.is_active
        context.connection_record = connection

        responder = DispatcherResponder(
            send,
            context,
            connection_id=connection and connection.connection_id,
            reply_socket_id=delivery.socket_id,
            reply_to_verkey=delivery.sender_verkey,
        )

        if error_result:
            return asyncio.ensure_future(responder.send_reply(error_result))

        handler_cls = context.message.Handler
        handler = asyncio.ensure_future(handler_cls().handle(context, responder))
        return handler

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


class DispatcherResponder(BaseResponder):
    """Handle outgoing messages from message handlers."""

    def __init__(self, send: Coroutine, context: RequestContext, **kwargs):
        """
        Initialize an instance of `DispatcherResponder`.

        Args:
            send: Function to send outbound message
            context: The request context of the incoming message

        """
        super().__init__(**kwargs)
        self._context = context
        self._send = send

    async def create_outbound(
        self, message: Union[AgentMessage, str, bytes], **kwargs
    ) -> OutboundMessage:
        """Create an OutboundMessage from a message body."""
        if isinstance(message, AgentMessage) and self._context.settings.get(
            "timing.enabled"
        ):
            # Inject the timing decorator
            in_time = (
                self._context.message_delivery
                and self._context.message_delivery.in_time
            )
            if not message._timing:
                message._timing = TimingDecorator(
                    in_time=in_time, out_time=datetime_now()
                )
        return await super().create_outbound(message, **kwargs)

    async def send_outbound(self, message: OutboundMessage):
        """
        Send outbound message.

        Args:
            message: The `OutboundMessage` to be sent
        """
        await self._send(message)
