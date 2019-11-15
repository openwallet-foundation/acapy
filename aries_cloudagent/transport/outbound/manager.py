"""Outbound transport manager."""

import asyncio
import logging
import time

from typing import Type, Union
from urllib.parse import urlparse

from ...classloader import ClassLoader, ModuleLoadError, ClassNotFoundError
from ...config.injection_context import InjectionContext
from ...messaging.task_queue import TaskQueue
from ...stats import Collector

from ..wire_format import BaseWireFormat

from .base import (
    BaseOutboundTransport,
    OutboundDeliveryError,
    OutboundTransportRegistrationError,
)
from .message import OutboundMessage

LOGGER = logging.getLogger(__name__)
MODULE_BASE_PATH = "aries_cloudagent.transport.outbound"


class QueuedOutboundMessage:
    STATE_NEW = "new"
    STATE_PENDING = "pending"
    STATE_ENCODE = "encode"
    STATE_DELIVER = "deliver"
    STATE_RETRY = "retry"
    STATE_DONE = "done"

    def __init__(
        self,
        context: InjectionContext,
        message: OutboundMessage,
        target,
        transport_id: str,
    ):
        self.context = context
        self.endpoint = target and target.endpoint
        self.error: Exception = None
        self.message = message
        self.payload: Union[str, bytes] = None
        self.retries = 0
        self.retry_at: float = None
        self.state = self.STATE_NEW
        self.target = target
        self.task: asyncio.Task = None
        self.transport_id: str = transport_id


class OutboundTransportManager:
    """Outbound transport manager class."""

    def __init__(self, context: InjectionContext, run_task=None):
        """
        Initialize a `OutboundTransportManager` instance.

        Args:
            queue: `BaseOutboundMessageQueue` instance to use

        """
        self.context = context
        self.registered_schemes = {}
        self.registered_transports = {}
        self.running_transports = {}
        self.outbound_buffer = []
        self.outbound_event = asyncio.Event()
        self.outbound_new = []
        self.process_task: asyncio.Task = None
        self.run_task = run_task
        self.task_queue = TaskQueue(max_active=50)

    async def setup(self):
        outbound_transports = (
            self.context.settings.get("transport.outbound_configs") or []
        )
        for outbound_transport in outbound_transports:
            self.register(outbound_transport)

    def register(self, module: str) -> str:
        """
        Register a new outbound transport by module path.

        Args:
            module: Module name to register

        Raises:
            OutboundTransportRegistrationError: If the imported class cannot
                be located
            OutboundTransportRegistrationError: If the imported class does not
                specify a schemes attribute
            OutboundTransportRegistrationError: If the scheme has already been
                registered

        """
        try:
            imported_class = ClassLoader.load_subclass_of(
                BaseOutboundTransport, module, MODULE_BASE_PATH
            )
        except (ModuleLoadError, ClassNotFoundError):
            raise OutboundTransportRegistrationError(
                f"Outbound transport module {module} could not be resolved."
            )

        return self.register_class(imported_class)

    def register_class(self, transport_class: Type[BaseOutboundTransport]) -> str:
        """
        Register a new outbound transport class.

        Args:
            transport_class: Transport class to register

        Raises:
            OutboundTransportRegistrationError: If the imported class does not
                specify a schemes attribute
            OutboundTransportRegistrationError: If the scheme has already been
                registered

        """
        try:
            schemes = transport_class.schemes
        except AttributeError:
            raise OutboundTransportRegistrationError(
                f"Imported class {transport_class} does not "
                + "specify a required 'schemes' attribute"
            )
        transport_id = transport_class.__qualname__

        for scheme in schemes:
            if scheme in self.registered_schemes:
                # A scheme can only be registered once
                raise OutboundTransportRegistrationError(
                    f"Cannot register transport '{transport_id}'"
                    f"for '{scheme}' scheme because the scheme"
                    "has already been registered"
                )

        self.registered_transports[transport_id] = transport_class

        for scheme in schemes:
            self.registered_schemes[scheme] = transport_id

        return transport_id

    async def start_transport(self, transport_id: str):
        """Start the transport."""
        transport = self.registered_transports[transport_id]()
        transport.collector = await self.context.inject(Collector, required=False)
        await transport.start()
        self.running_transports[transport_id] = transport

    async def start(self):
        """Start all transports and feed messages from the queue."""
        for transport_id in self.registered_transports:
            self.task_queue.run(self.start_transport(transport_id))
        self.process_task = asyncio.get_event_loop().create_task(self.process_queued())

    async def stop(self, wait: bool = True):
        """Stop all transports."""
        if self.process_task:
            if not self.process_task.done():
                self.process_task.cancel()
            self.process_task = None
        await self.task_queue.complete(None if wait else 0)
        for transport in self.running_transports.values():
            await transport.stop()
        self.running_transports = {}

    def get_registered_transport_for_scheme(self, scheme: str) -> str:
        """Find the registered transport for a given scheme."""
        try:
            return next(
                transport_id
                for transport_id, transport in self.registered_transports.items()
                if scheme in transport.schemes
            )
        except StopIteration:
            pass

    def get_running_transport_for_scheme(self, scheme: str) -> str:
        """Find the running transport for a given scheme."""
        try:
            return next(
                transport_id
                for transport_id, transport in self.running_transports.items()
                if scheme in transport.schemes
            )
        except StopIteration:
            pass

    def get_running_transport_for_endpoint(self, endpoint: str):
        """Find the running transport to use for a given endpoint."""
        # Grab the scheme from the uri
        scheme = urlparse(endpoint).scheme
        if scheme == "":
            raise OutboundDeliveryError(
                f"The uri '{endpoint}' does not specify a scheme"
            )

        # Look up transport that is registered to handle this scheme
        transport_id = self.get_running_transport_for_scheme(scheme)
        if not transport_id:
            raise OutboundDeliveryError(
                f"No transport driver exists to handle scheme '{scheme}'"
            )
        return transport_id

    def get_transport(self, transport_id: str):
        return self.running_transports[transport_id]

    def deliver(self, context: InjectionContext, outbound: OutboundMessage):
        targets = [outbound.target] if outbound.target else (outbound.target_list or [])
        transport_id = None
        for target in targets:
            endpoint = target.endpoint
            try:
                transport_id = self.get_running_transport_for_endpoint(endpoint)
            except OutboundDeliveryError:
                pass
            if transport_id:
                break
        if not transport_id:
            raise OutboundDeliveryError("No supported transport for outbound message")

        queued = QueuedOutboundMessage(context, outbound, target, transport_id)
        self.outbound_new.append(queued)
        self.outbound_event.set()

    async def process_queued(self):
        """Continually watch the outbound buffer and send to transports."""

        while True:
            # if self.stopping .. break

            self.outbound_event.clear()
            loop_time = time.perf_counter()
            upd_buffer = []

            for queued in self.outbound_buffer:
                if queued.state == QueuedOutboundMessage.STATE_DONE:
                    if queued.error:
                        LOGGER.exception(
                            "Outbound message could not be delivered",
                            exc_info=queued.error,
                        )
                    continue  # remove from buffer

                deliver = False

                if queued.state == QueuedOutboundMessage.STATE_PENDING:
                    deliver = True
                elif queued.state == QueuedOutboundMessage.STATE_RETRY:
                    if queued.retry_at < loop_time:
                        queued.retry_at = None
                        deliver = True

                if deliver:
                    queued.state = QueuedOutboundMessage.STATE_DELIVER
                    self.deliver_queued_message(queued)

                upd_buffer.append(queued)

            new_messages = self.outbound_new.copy()
            self.outbound_new = []
            for queued in new_messages:

                if queued.message.enc_payload:
                    queued.payload = queued.message.enc_payload
                    queued.state = QueuedOutboundMessage.STATE_DELIVER
                    self.deliver_queued_message(queued)
                else:
                    queued.state = QueuedOutboundMessage.STATE_ENCODE
                    await self.encode_queued_message(queued)

                upd_buffer.append(queued)

            self.outbound_buffer = upd_buffer
            await self.outbound_event.wait()

    async def encode_queued_message(
        self, queued: QueuedOutboundMessage
    ) -> asyncio.Task:
        transport = self.get_transport(queued.transport_id)
        wire_format = transport.wire_format or await queued.context.inject(
            BaseWireFormat
        )
        queued.task = (self.run_task or self.task_queue.run)(
            wire_format.encode_message(
                queued.context,
                queued.message.payload,
                queued.target.recipient_keys,
                queued.target.routing_keys,
                queued.target.sender_key,
            ),
            lambda task, exc_info: self.finished_encode(queued, task, exc_info),
        )
        return queued.task

    def finished_encode(
        self, queued: QueuedOutboundMessage, task: asyncio.Task, exc_info=None
    ):
        if exc_info:
            queued.error = exc_info
            queued.state = QueuedOutboundMessage.STATE_DONE
        else:
            queued.payload = task.result()
            queued.state = QueuedOutboundMessage.STATE_PENDING
        queued.task = None
        self.outbound_event.set()

    def deliver_queued_message(self, queued: QueuedOutboundMessage) -> asyncio.Task:
        transport = self.get_transport(queued.transport_id)
        queued.task = self.task_queue.run(
            transport.handle_message(queued.payload, queued.endpoint),
            lambda task, exc_info: self.finished_deliver(queued, task, exc_info),
        )
        return queued.task

    def finished_deliver(
        self, queued: QueuedOutboundMessage, task: asyncio.Task, exc_info=None
    ):
        """Clean up a closed session."""
        if exc_info:
            queued.error = exc_info
            if queued.retries < 5:
                queued.state = QueuedOutboundMessage.STATE_RETRY
                queued.retry_at = time.perf_counter() + 10
            else:
                queued.state = QueuedOutboundMessage.STATE_DONE
        else:
            queued.error = None
            queued.state = QueuedOutboundMessage.STATE_DONE
        queued.task = None
        self.outbound_event.set()
