"""Outbound transport manager."""

import asyncio
import logging

from typing import Type
from urllib.parse import urlparse

from ...classloader import ClassLoader, ModuleLoadError, ClassNotFoundError
from ...messaging.outbound_message import OutboundMessage

from .base import BaseOutboundTransport, OutboundTransportRegistrationError
from .queue.base import BaseOutboundMessageQueue


MODULE_BASE_PATH = "aries_cloudagent.transport.outbound"


class OutboundTransportManager:
    """Outbound transport manager class."""

    def __init__(self, queue_class: Type[BaseOutboundMessageQueue]):
        """
        Initialize a `OutboundTransportManager` instance.

        Args:
            queue: `BaseOutboundMessageQueue` implementation to use

        """
        self.logger = logging.getLogger(__name__)
        self.registered_transports = {}
        self.running_tasks = None
        self.running_transports = {}
        self.class_loader = ClassLoader(MODULE_BASE_PATH, BaseOutboundTransport)
        self.queue_class = queue_class

    def register(self, module_path):
        """
        Register a new outbound transport by module path.

        Args:
            module_path: Module path to register

        Raises:
            OutboundTransportRegistrationError: If the imported class cannot
                be located
            OutboundTransportRegistrationError: If the imported class does not
                specify a schemes attribute
            OutboundTransportRegistrationError: If the scheme has already been
                registered

        """
        try:
            imported_class = self.class_loader.load(module_path, True)
        except (ModuleLoadError, ClassNotFoundError):
            raise OutboundTransportRegistrationError(
                f"Outbound transport module {module_path} could not be resolved."
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

    async def start_transport(self, schemes, transport):
        """Start the transport."""
        # All transports share the same queue class
        async with transport(self.queue_class()) as t:
            self.running_transports[schemes] = t
            await t.start()

    async def start_all(self):
        """Start all transports."""
        startup = []
        for schemes, transport_class in self.registered_transports.items():
            # Don't block the loop
            startup.append(
                asyncio.ensure_future(self.start_transport(schemes, transport_class))
            )
        self.running_tasks = startup

    async def stop_all(self):
        """Stop all transports."""
        if self.running_tasks:
            for task in self.running_tasks:
                task.cancel()
            self.running_tasks = None
        self.running_transports = {}

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
        Send a message.

        Find a registered transport for the scheme in the uri and
        use it to send the message.

        Args:
            message: The outbound message to send

        """
        # Grab the scheme from the uri
        scheme = urlparse(message.endpoint).scheme
        if scheme == "":
            self.logger.warn(f"The uri '{message.endpoint}' does not specify a scheme")
            return

        # Look up transport that is registered to handle this scheme
        transport = self.get_running_transport_for_scheme(scheme)
        if not transport:
            self.logger.warn(f"No transport driver exists to handle scheme '{scheme}'")
            return

        await transport.enqueue(message)
