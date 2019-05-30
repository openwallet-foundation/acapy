"""Inbound transport manager."""

import logging

from .base import BaseInboundTransport
from ...classloader import ClassLoader, ModuleLoadError, ClassNotFoundError

MODULE_BASE_PATH = "indy_catalyst_agent.transport.inbound"


class InboundTransportManager:
    """Inbound transport manager class."""

    def __init__(self):
        """Initialize an `InboundTransportManager` instance."""
        self.logger = logging.getLogger(__name__)
        self.class_loader = ClassLoader(MODULE_BASE_PATH, BaseInboundTransport)

        self.transports = []

    def register(self, module_path, host, port, message_handler, register_socket):
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
            imported_class = self.class_loader.load(module_path, True)
        except (ModuleLoadError, ClassNotFoundError):
            self.logger.warning(f"Failed to load module {module_path}")
            return

        self.transports.append(
            imported_class(host, port, message_handler, register_socket)
        )

    async def start_all(self):
        """Start all registered transports."""
        for transport in self.transports:
            await transport.start()
