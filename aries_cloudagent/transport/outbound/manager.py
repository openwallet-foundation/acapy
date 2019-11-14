"""Outbound transport manager."""

import asyncio
import logging

from typing import Type
from urllib.parse import urlparse

from ...error import BaseError
from ...classloader import ClassLoader, ModuleLoadError, ClassNotFoundError
from ...stats import Collector

from .base import BaseOutboundTransport, OutboundTransportRegistrationError

LOGGER = logging.getLogger(__name__)
MODULE_BASE_PATH = "aries_cloudagent.transport.outbound"


class OutboundDeliveryError(BaseError):
    """Base exception when a message cannot be delivered via an outbound transport."""


class OutboundTransportManager:
    """Outbound transport manager class."""

    def __init__(self, collector: Collector = None):
        """
        Initialize a `OutboundTransportManager` instance.

        Args:
            queue: `BaseOutboundMessageQueue` instance to use

        """
        self.logger = logging.getLogger(__name__)
        self.registered_schemes = {}
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

    async def start_transport(self, transport_id: str):
        """Start the transport."""
        transport = self.registered_transports[transport_id]()
        transport.collector = self.collector
        await transport.start()
        self.running_transports[transport_id] = transport

    async def start(self):
        """Start all transports and feed messages from the queue."""
        startup = []
        loop = asyncio.get_event_loop()
        for transport_id in self.registered_transports:
            # Don't block the loop
            startup.append(loop.create_task(self.start_transport(transport_id)))
        self.startup_tasks = startup

    async def stop(self, wait: bool = True):
        """Stop all transports."""
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
