import asyncio
import logging

from importlib import import_module
from typing import Type
from urllib.parse import urlparse

from .base import BaseOutboundTransport
from ...classloader import ClassLoader, ModuleLoadError, ClassNotFoundError
from ...error import BaseError
from .queue.base import BaseOutboundMessageQueue
from .message import OutboundMessage
from ...models.connection_target import ConnectionTarget

MODULE_BASE_PATH = "indy_catalyst_agent.transport.outbound"


class OutboundTransportRegistrationError(BaseError):
    pass


class OutboundTransportManager:
    def __init__(self, queue: Type[BaseOutboundMessageQueue]):
        self.logger = logging.getLogger(__name__)
        self.registered_transports = {}
        self.running_transports = {}
        self.class_loader = ClassLoader(MODULE_BASE_PATH, BaseOutboundTransport)
        self.queue = queue

    def register(self, module_path):
        imported_class = self.class_loader.load(module_path, True)

        try:
            schemes = imported_class.schemes
        except AttributeError:
            raise OutboundTransportRegistrationError(
                f"Imported class {imported_class} does not specify a required 'schemes' attribute"
            )

        for scheme in schemes:
            # A scheme can only be registered once
            for scheme_tuple in self.registered_transports.keys():
                if scheme in scheme_tuple:
                    raise OutboundTransportRegistrationError(
                        f"Cannot register transport '{module_path}' for '{scheme}' scheme"
                        + f" because the scheme has already been registered"
                    )

        self.registered_transports[schemes] = imported_class

    async def start(self, schemes, transport):
        # All transports share the same queue
        async with transport(self.queue()) as t:
            self.running_transports[schemes] = t
            await t.start()

    async def start_all(self):
        for schemes, transport_class in self.registered_transports.items():
            # Don't block the loop
            # asyncio.create_task(self.start(schemes, transport_class))
            asyncio.ensure_future(self.start(schemes, transport_class))

    async def send_message(self, message, target: ConnectionTarget):
        # Grab the scheme from the uri
        scheme = urlparse(target.endpoint).scheme
        if scheme == "":
            self.logger.warn(f"The uri '{target.endpoint}' does not specify a scheme")
            return

        # Look up transport that is registered to handle this scheme
        try:
            transport = next(
                transport
                for schemes, transport in self.running_transports.items()
                if scheme in schemes
            )
        except StopIteration:
            self.logger.warn(f"No transport driver exists to handle scheme '{scheme}'")
            return

        message = OutboundMessage(data=message, target=target)
        await transport.queue.enqueue(message)
