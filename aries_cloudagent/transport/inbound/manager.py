"""Inbound transport manager."""

import logging

from .base import (
    BaseInboundTransport,
    InboundTransportConfiguration,
    InboundTransportRegistrationError,
)
from ...classloader import ClassLoader, ModuleLoadError, ClassNotFoundError

MODULE_BASE_PATH = "aries_cloudagent.transport.inbound"


class InboundTransportManager:
    """Inbound transport manager class."""

    def __init__(self):
        """Initialize an `InboundTransportManager` instance."""
        self.logger = logging.getLogger(__name__)
        self.registered_transports = []

    def register(
        self, config: InboundTransportConfiguration, message_handler, register_socket
    ):
        """
        Register transport module.

        Args:
            module_path: Path to module
            host: The host to register on
            port: The port to register on
            message_handler: The message handler for incoming messages
            register_socket: A coroutine for registering a new socket

        """
        try:
            imported_class = ClassLoader.load_subclass_of(
                BaseInboundTransport, config.module, MODULE_BASE_PATH
            )
        except (ModuleLoadError, ClassNotFoundError) as e:
            raise InboundTransportRegistrationError(
                f"Failed to load inbound transport {config.module}"
            ) from e

        instance = imported_class(
            config.host, config.port, message_handler, register_socket
        )
        self.register_instance(instance)

    def register_instance(self, transport: BaseInboundTransport):
        """
        Register a new inbound transport instance.

        Args:
            transport: Inbound transport instance to register

        """
        self.registered_transports.append(transport)

    async def start(self):
        """Start all registered transports."""
        for transport in self.registered_transports:
            await transport.start()

    async def stop(self):
        """Stop all registered transports."""
        for transport in self.registered_transports:
            await transport.stop()
