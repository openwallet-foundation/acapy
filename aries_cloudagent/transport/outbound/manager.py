"""Outbound transport manager."""

import asyncio
import logging
import uuid

from typing import Type
from urllib.parse import urlparse

from ...error import BaseError
from ...classloader import ClassLoader, ModuleLoadError, ClassNotFoundError
from ...messaging.outbound_message import OutboundMessage
from ...stats import Collector
from ...task_processor import TaskProcessor

from .base import BaseOutboundTransport, OutboundTransportRegistrationError
from .queue.base import BaseOutboundMessageQueue


MODULE_BASE_PATH = "aries_cloudagent.transport.outbound"


class OutboundDeliveryError(BaseError):
    """Base exception when a message cannot be delivered via an outbound transport."""


class OutboundTransportManager:
    """Outbound transport manager class."""

    def __init__(
        self, queue: BaseOutboundMessageQueue = None, collector: Collector = None
    ):
        """
        Initialize a `OutboundTransportManager` instance.

        Args:
            queue: `BaseOutboundMessageQueue` instance to use

        """
        self.logger = logging.getLogger(__name__)
        self.polling_task = None
        self.processor: TaskProcessor = None
        self.queue: BaseOutboundMessageQueue = queue
        self.registered_transports = {}
        self.running_transports = {}
        self.startup_tasks = []
        self.collector = collector

    def register(self, module: str):
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

        self.register_class(imported_class)

    def register_class(self, transport_class: Type[BaseOutboundTransport]):
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

        for scheme in schemes:
            # A scheme can only be registered once
            for scheme_tuple in self.registered_transports.keys():
                if scheme in scheme_tuple:
                    raise OutboundTransportRegistrationError(
                        f"Cannot register transport '{transport_class.__qualname__}'"
                        + f"for '{scheme}' scheme because the scheme"
                        + "has already been registered"
                    )

        self.registered_transports[tuple(schemes)] = transport_class

    async def start_transport(self, schemes, transport_cls):
        """Start the transport."""
        transport = transport_cls()
        transport.collector = self.collector
        await transport.start()
        self.running_transports[schemes] = transport

    async def start(self):
        """Start all transports and feed messages from the queue."""
        startup = []
        loop = asyncio.get_event_loop()
        for schemes, transport_class in self.registered_transports.items():
            # Don't block the loop
            startup.append(
                loop.create_task(self.start_transport(schemes, transport_class))
            )
        self.startup_tasks = startup
        self.polling_task = loop.create_task(self.poll())

    async def stop(self, wait: bool = True):
        """Stop all transports."""
        self.queue.stop()
        if wait:
            await self.queue.join()
        if self.polling_task:
            if wait:
                await self.polling_task
            elif not self.polling_task.done:
                self.polling_task.cancel()
            self.polling_task = None
        for transport in self.running_transports.values():
            await transport.stop()
        if self.startup_tasks:
            for task in self.startup_tasks:
                if wait:
                    await task
                elif not task.done():
                    task.cancel()
            self.startup_tasks = []
        self.running_transports = {}

    async def poll(self):
        """Send messages from the queue to the transports."""
        self.processor = TaskProcessor(max_pending=10)
        async for message in self.queue:
            unique = str(uuid.uuid4)
            self.logger.debug(f"Processing message from queue. id: {unique}")
            await self.processor.run_retry(
                lambda pending, msg=message: self.dispatch_message(
                    msg, pending.attempts + 1
                ),
                retries=5,
                retry_delay=10.0,
            )
            self.logger.debug(f"Done processing message from queue id: {unique}")
            self.queue.task_done()

        await self.processor.wait_done()

    def get_registered_transport_for_scheme(self, scheme: str):
        """Find the registered transport for a given scheme."""
        try:
            return next(
                transport
                for schemes, transport in self.registered_transports.items()
                if scheme in schemes
            )
        except StopIteration:
            pass

    def get_running_transport_for_scheme(self, scheme: str):
        """Find the running transport for a given scheme."""
        try:
            return next(
                transport
                for schemes, transport in self.running_transports.items()
                if scheme in schemes
            )
        except StopIteration:
            pass

    async def send_message(self, message: OutboundMessage):
        """
        Add a message to the outbound queue.

        Args:
            message: The outbound message to send

        """
        if self.queue:
            await self.queue.enqueue(message)
        else:
            await self.dispatch_message(message)

    async def dispatch_message(self, message: OutboundMessage, attempt: int = None):
        """Dispatch a message to the relevant transport.

        Find a registered transport for the scheme in the uri and
        use it to send the message.

        Args:
            message: The outbound message to dispatch

        """
        # Grab the scheme from the uri
        scheme = urlparse(message.endpoint).scheme
        if scheme == "":
            raise OutboundDeliveryError(
                f"The uri '{message.endpoint}' does not specify a scheme"
            )

        # Look up transport that is registered to handle this scheme
        transport = self.get_running_transport_for_scheme(scheme)
        if not transport:
            raise OutboundDeliveryError(
                f"No transport driver exists to handle scheme '{scheme}'"
            )

        # TODO log delivery error on final attempt
        await transport.handle_message(message)
