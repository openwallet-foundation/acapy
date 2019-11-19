"""
The Dispatcher.

The dispatcher is responsible for coordinating data flow between handlers, providing
lifecycle hook callbacks storing state for message threads, etc.
"""

import asyncio
import logging
from typing import Callable, Coroutine, Union

from .config.injection_context import InjectionContext
from .messaging.agent_message import AgentMessage
from .messaging.error import MessageParseError
from .messaging.models.base import BaseModelError
from .protocols.connections.manager import ConnectionManager
from .protocols.problem_report.message import ProblemReport
from .messaging.protocol_registry import ProtocolRegistry
from .messaging.request_context import RequestContext
from .messaging.responder import BaseResponder
from .messaging.task_queue import TaskQueue
from .messaging.util import datetime_now
from .stats import Collector
from .transport.inbound.message import InboundMessage
from .transport.outbound.message import OutboundMessage

LOGGER = logging.getLogger(__name__)


class Dispatcher:
    """
    Dispatcher class.

    Class responsible for dispatching messages to message handlers and responding
    to other agents.
    """

    def __init__(self, context: InjectionContext):
        """Initialize an instance of Dispatcher."""
        self.context = context
        self.task_queue = TaskQueue(max_active=20)

    def put_task(self, coro: Coroutine, complete: Callable = None) -> asyncio.Future:
        """Run a task in the task queue, potentially blocking other handlers."""
        return self.task_queue.put(coro, complete)

    def run_task(self, coro: Coroutine, complete: Callable = None) -> asyncio.Task:
        """Run a task in the task queue, potentially blocking other handlers."""
        return self.task_queue.run(coro, complete)

    def queue_message(
        self,
        inbound_message: InboundMessage,
        send_outbound: Coroutine,
        send_webhook: Coroutine = None,
        complete: Callable = None,
    ) -> asyncio.Future:
        """
        Add a message to the processing queue for handling.

        Args:
            inbound_message: The inbound message instance
            send_outbound: Async function to send outbound messages
            send_webhook: Async function to dispatch a webhook
            complete: Function to call when the handler has completed

        Returns:
            A future resolving to the handler task

        """
        return self.put_task(
            self.handle_message(inbound_message, send_outbound, send_webhook), complete
        )

    async def handle_message(
        self,
        inbound_message: InboundMessage,
        send_outbound: Coroutine,
        send_webhook: Coroutine = None,
    ):
        """
        Configure responder and message context and invoke the message handler.

        Args:
            inbound_message: The inbound message instance
            send_outbound: Async function to send outbound messages
            send_webhook: Async function to dispatch a webhook

        Returns:
            The response from the handler

        """

        connection_mgr = ConnectionManager(self.context)
        connection = await connection_mgr.find_inbound_connection(
            inbound_message.receipt
        )
        if connection:
            inbound_message.connection_id = connection.connection_id

        error_result = None
        try:
            message = await self.make_message(inbound_message.payload)
        except MessageParseError as e:
            LOGGER.error(f"Message parsing failed: {str(e)}, sending problem report")
            error_result = ProblemReport(explain_ltxt=str(e))
            if inbound_message.receipt.thread_id:
                error_result.assign_thread_id(inbound_message.receipt.thread_id)
            message = None

        context = RequestContext(base_context=self.context)
        context.message = message
        context.message_receipt = inbound_message.receipt
        context.connection_ready = connection and connection.is_ready
        context.connection_record = connection

        responder = DispatcherResponder(
            context,
            inbound_message,
            send_outbound,
            send_webhook,
            connection_id=connection and connection.connection_id,
            reply_session_id=inbound_message.session_id,
            reply_to_verkey=inbound_message.receipt.sender_verkey,
        )

        if error_result:
            await responder.send_reply(error_result)
            return

        context.injector.bind_instance(BaseResponder, responder)

        handler_cls = context.message.Handler
        handler_obj = handler_cls()
        collector: Collector = await context.inject(Collector, required=False)
        if collector:
            collector.wrap(handler_obj, "handle", ["any-message-handler"])
        await handler_obj.handle(context, responder)

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

        registry: ProtocolRegistry = await self.context.inject(ProtocolRegistry)
        message_type = parsed_msg.get("@type")
        if not message_type:
            raise MessageParseError("Message does not contain '@type' parameter")

        message_cls = registry.resolve_message_class(message_type)
        if not message_cls:
            raise MessageParseError(f"Unrecognized message type {message_type}")

        try:
            instance = message_cls.deserialize(parsed_msg)
        except BaseModelError as e:
            raise MessageParseError(f"Error deserializing message: {e}") from e

        return instance


class DispatcherResponder(BaseResponder):
    """Handle outgoing messages from message handlers."""

    def __init__(
        self,
        context: RequestContext,
        inbound_message: InboundMessage,
        send_outbound: Coroutine,
        send_webhook: Coroutine = None,
        **kwargs,
    ):
        """
        Initialize an instance of `DispatcherResponder`.

        Args:
            context: The request context of the incoming message
            inbound_message: The inbound message triggering this handler
            send_outbound: Async function to send outbound message
            send_webhook: Async function to dispatch a webhook

        """
        super().__init__(**kwargs)
        self._context = context
        self._inbound_message = inbound_message
        self._send = send_outbound
        self._webhook = send_webhook

    async def create_outbound(
        self, message: Union[AgentMessage, str, bytes], **kwargs
    ) -> OutboundMessage:
        """
        Create an OutboundMessage from a message body.

        Args:
            message: The message payload
        """
        if isinstance(message, AgentMessage) and self._context.settings.get(
            "timing.enabled"
        ):
            # Inject the timing decorator
            in_time = (
                self._context.message_receipt and self._context.message_receipt.in_time
            )
            if not message._decorators.get("timing"):
                message._decorators["timing"] = {
                    "in_time": in_time,
                    "out_time": datetime_now(),
                }
        return await super().create_outbound(message, **kwargs)

    async def send_outbound(self, message: OutboundMessage):
        """
        Send outbound message.

        Args:
            message: The `OutboundMessage` to be sent
        """
        await self._send(self._context, message, self._inbound_message)

    async def send_webhook(self, topic: str, payload: dict):
        """
        Dispatch a webhook.

        Args:
            topic: the webhook topic identifier
            payload: the webhook payload value
        """
        if self._webhook:
            await self._webhook(topic, payload)
