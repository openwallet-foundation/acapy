import logging
from importlib import import_module

from .base import BaseInboundTransport
from ...classloader import ClassLoader, ModuleLoadError, ClassNotFoundError

MODULE_BASE_PATH = "indy_catalyst_agent.transport.inbound"


class InboundTransportManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.class_loader = ClassLoader(MODULE_BASE_PATH, BaseInboundTransport)

        self.transports = []

    def register(self, module_path, host, port, message_handler):
        try:
            imported_class = self.class_loader.load(module_path, True)
        except (ModuleLoadError, ClassNotFoundError):
            self.logger.warning(f"Failed to load module {module_path}")
            return

        self.transports.append(imported_class(host, port, message_handler))

    async def start_all(self):
        for transport in self.transports:
            await transport.start()
