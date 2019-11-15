"""Inbound transport manager."""

import asyncio
import logging
import uuid
from collections import OrderedDict
from typing import Coroutine

from ...config.injection_context import InjectionContext
from ...classloader import ClassLoader, ModuleLoadError, ClassNotFoundError
from ...messaging.task_queue import CompletedTask, TaskQueue
from ...delivery_queue import DeliveryQueue

from ..outbound.message import OutboundMessage
from ..wire_format import BaseWireFormat

from .base import (
    BaseInboundTransport,
    InboundTransportConfiguration,
    InboundTransportRegistrationError,
)
from .session import InboundSession

LOGGER = logging.getLogger(__name__)
MODULE_BASE_PATH = "aries_cloudagent.transport.inbound"


class InboundTransportManager:
    """Inbound transport manager class."""

    def __init__(self, context: InjectionContext, receive_inbound: Coroutine):
        """Initialize an `InboundTransportManager` instance."""
        self.context = context
        self.receive_inbound = receive_inbound
        self.registered_transports = {}
        self.running_transports = {}
        self.sessions = OrderedDict()
        self.session_limit: asyncio.Semaphore = None
        self.task_queue = TaskQueue()
        self.undelivered_queue: DeliveryQueue = None

    async def setup(self):
        """Perform setup operations."""
        inbound_transports = (
            self.context.settings.get("transport.inbound_configs") or []
        )
        for transport in inbound_transports:
            module, host, port = transport
            self.register(
                InboundTransportConfiguration(module=module, host=host, port=port)
            )

        # Setup queue for undelivered messages
        if self.context.settings.get("transport.enable_undelivered_queue"):
            self.undelivered_queue = DeliveryQueue()

        # self.session_limit = asyncio.Semaphore(50)

    def register(self, config: InboundTransportConfiguration) -> str:
        """
        Register transport module.

        Args:
            config: The inbound transport configuration

        """
        try:
            imported_class = ClassLoader.load_subclass_of(
                BaseInboundTransport, config.module, MODULE_BASE_PATH
            )
        except (ModuleLoadError, ClassNotFoundError) as e:
            raise InboundTransportRegistrationError(
                f"Failed to load inbound transport {config.module}"
            ) from e

        return self.register_transport(
            imported_class(config.host, config.port, self.create_session),
            imported_class.__qualname__,
        )

    def register_transport(
        self, transport: BaseInboundTransport, transport_id: str
    ) -> str:
        """
        Register a new inbound transport class.

        Args:
            transport: Transport instance to register
            transport_id: The transport ID to register

        """
        self.registered_transports[transport_id] = transport

    async def start_transport(self, transport_id: str):
        """
        Start a registered inbound transport.

        Args:
            transport_id: ID for the inbound transport to start

        """
        transport = self.registered_transports[transport_id]
        await transport.start()
        self.running_transports[transport_id] = transport

    def get_transport_instance(self, transport_id: str) -> BaseInboundTransport:
        """Get an instance of a running transport by ID."""
        return self.running_transports[transport_id]

    async def start(self):
        """Start all registered transports."""
        for transport_id in self.registered_transports:
            self.task_queue.run(self.start_transport(transport_id))

    async def stop(self, wait: bool = True):
        """Stop all registered transports."""
        await self.task_queue.complete(None if wait else 0)
        for transport in self.running_transports.values():
            await transport.stop()

    async def create_session(
        self,
        transport_type: str,
        client_info: dict = None,
        wire_format: BaseWireFormat = None,
    ):
        """Create a new inbound session."""
        if self.session_limit:
            await self.session_limit
        if not wire_format:
            wire_format = await self.context.inject(BaseWireFormat)
        session = InboundSession(
            context=self.context,
            client_info=client_info,
            close_handler=self.closed_session,
            inbound_handler=self.receive_inbound,
            session_id=str(uuid.uuid4()),
            transport_type=transport_type,
            wire_format=wire_format,
        )
        self.sessions[session.session_id] = session
        return session

    def dispatch_complete(self, message, completed: CompletedTask):
        """Handle completion of message dispatch."""
        session = self.sessions.get(message.session_id)
        if session:
            # need to scan the undelivered queue and see if anything is queued
            # for this session first
            session.dispatch_complete(message)

    def closed_session(self, session: InboundSession):
        """Clean up a closed session."""
        if session.session_id in self.sessions:
            del self.sessions[session.session_id]
            if self.session_limit:
                self.session_limit.release()
        # FIXME if there is a message in the outbound buffer, re-queue it

    async def queue_processing(self, session: InboundSession):
        """
        Interact with undelivered queue to find applicable messages.

        Args:
            session: The inbound session
        """
        if (
            session
            and session.reply_mode
            and not session.closed
            and self.undelivered_queue
        ):
            for key in session.reply_verkeys:
                if not isinstance(key, str):
                    key = key.value
                if self.undelivered_queue.has_message_for_key(key):
                    for (
                        undelivered_message
                    ) in self.undelivered_queue.inspect_all_messages_for_key(key):
                        # pending message. Transmit, then kill single_response
                        if session.select_outbound(undelivered_message):
                            LOGGER.debug(
                                "Sending Queued Message via inbound connection"
                            )
                            self.undelivered_queue.remove_message_for_key(
                                key, undelivered_message
                            )
                            await session.send(undelivered_message)

    def return_to_session(self, outbound: OutboundMessage):
        """Return an outbound message to an open session, if possible."""
        # if outbound.reply_session_id:

        # if inbound and inbound.receipt.

        #  if the message has multiple targets, we cannot direct return unless
        #  one of the targets has keys that match the inbound message (!)
        # if an

        accepted = False

        # try open inbound sessions first, preferring the same session ID
        # FIXME if outbound target is set, need to compare to inbound keys

        if not outbound.target:
            session = self.sessions.get(outbound.reply_session_id)
            if session:
                accepted, retry = session.accept_response(outbound)

            if not accepted:
                for session in self.session.values():
                    if session.session_id != outbound.reply_session_id:
                        accepted, retry = session.accept_response(outbound)
                        break

        if accepted:
            LOGGER.debug("Returned message to socket %s", session.session_id)
