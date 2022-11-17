"""Inbound transport manager."""

import logging
import uuid
from collections import OrderedDict
from typing import Callable, Coroutine

from ...core.profile import Profile
from ...utils.classloader import ClassLoader, ModuleLoadError, ClassNotFoundError
from ...utils.task_queue import CompletedTask, TaskQueue

from ..outbound.message import OutboundMessage
from ..wire_format import BaseWireFormat

from .base import (
    BaseInboundTransport,
    InboundTransportConfiguration,
    InboundTransportRegistrationError,
)
from .delivery_queue import DeliveryQueue
from .message import InboundMessage
from .session import InboundSession

LOGGER = logging.getLogger(__name__)
MODULE_BASE_PATH = "aries_cloudagent.transport.inbound"


class InboundTransportManager:
    """Inbound transport manager class."""

    def __init__(
        self,
        profile: Profile,
        receive_inbound: Coroutine,
        return_inbound: Callable = None,
    ):
        """Initialize an `InboundTransportManager` instance."""
        self.profile = profile
        self.max_message_size = 0
        self.receive_inbound = receive_inbound
        self.return_inbound = return_inbound
        self.registered_transports = {}
        self.running_transports = {}
        self.sessions = OrderedDict()
        self.task_queue = TaskQueue()
        self.undelivered_queue: DeliveryQueue = None

    async def setup(self):
        """Perform setup operations."""
        # Load config settings
        if self.profile.context.settings.get("transport.max_message_size"):
            self.max_message_size = self.profile.context.settings[
                "transport.max_message_size"
            ]

        inbound_transports = (
            self.profile.context.settings.get("transport.inbound_configs") or []
        )
        for transport in inbound_transports:
            module, host, port = transport
            self.register(
                InboundTransportConfiguration(module=module, host=host, port=port)
            )

        # Setup queue for undelivered messages
        if self.profile.context.settings.get("transport.enable_undelivered_queue"):
            self.undelivered_queue = DeliveryQueue()

    def register(self, config: InboundTransportConfiguration) -> str:
        """
        Register transport module.

        Args:
            config: The inbound transport configuration

        """
        try:
            if "." in config.module:
                package, module = config.module.split(".", 1)
            else:
                package = MODULE_BASE_PATH
                module = config.module

            imported_class = ClassLoader.load_subclass_of(
                BaseInboundTransport, module, package
            )
        except (ModuleLoadError, ClassNotFoundError) as e:
            raise InboundTransportRegistrationError(
                f"Failed to load inbound transport {config.module}"
            ) from e

        return self.register_transport(
            imported_class(
                config.host,
                config.port,
                self.create_session,
                max_message_size=self.max_message_size,
                root_profile=self.profile,
            ),
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
        *,
        accept_undelivered: bool = False,
        can_respond: bool = False,
        client_info: dict = None,
        wire_format: BaseWireFormat = None,
    ):
        """
        Create a new inbound session.

        Args:
            transport_type: The inbound transport identifier
            accept_undelivered: Flag for accepting undelivered messages
            can_respond: Flag indicating that the transport can send responses
            client_info: An optional dict describing the client
            wire_format: Override the wire format for this session
        """
        if not wire_format:
            wire_format = self.profile.context.inject(BaseWireFormat)
        session = InboundSession(
            profile=self.profile,
            accept_undelivered=accept_undelivered,
            can_respond=can_respond,
            client_info=client_info,
            close_handler=self.closed_session,
            inbound_handler=self.receive_inbound,
            session_id=str(uuid.uuid4()),
            transport_type=transport_type,
            wire_format=wire_format,
        )
        self.sessions[session.session_id] = session
        return session

    def dispatch_complete(self, message: InboundMessage, completed: CompletedTask):
        """Handle completion of message dispatch."""
        session: InboundSession = self.sessions.get(message.session_id)
        if session and session.accept_undelivered and not session.response_buffered:
            self.process_undelivered(session)

        message.dispatch_processing_complete()

    def closed_session(self, session: InboundSession):
        """
        Clean up a closed session.

        Returns an undelivered message to the caller if possible.
        """
        if session.session_id in self.sessions:
            del self.sessions[session.session_id]
        if session.response_buffer:
            if self.return_inbound:
                self.return_inbound(session.profile, session.response_buffer)
            else:
                LOGGER.warning("Message failed return delivery, will not be delivered")

    def return_to_session(self, outbound: OutboundMessage) -> bool:
        """Return an outbound message via an open session, if possible."""
        accepted = False

        # prefer the same session ID
        if outbound.reply_session_id and outbound.reply_session_id in self.sessions:
            session = self.sessions[outbound.reply_session_id]
            accepted = session.accept_response(outbound)

        if not accepted:
            for session in self.sessions.values():
                if session.session_id != outbound.reply_session_id:
                    accepted = session.accept_response(outbound)
                    if accepted:
                        break

        if accepted:
            LOGGER.debug("Returned message to socket %s", session.session_id)
        return accepted

    def return_undelivered(self, outbound: OutboundMessage) -> bool:
        """
        Add an undelivered message to the undelivered queue.

        At this point the message could not be associated with an inbound
        session and could not be delivered via an outbound transport.
        """
        if self.undelivered_queue:
            self.undelivered_queue.add_message(outbound)
            return True
        return False

    def process_undelivered(self, session: InboundSession):
        """
        Interact with undelivered queue to find applicable messages.

        Args:
            session: The inbound session
        """
        if session and session.can_respond and self.undelivered_queue:
            for key in session.reply_verkeys:
                for (
                    undelivered_message
                ) in self.undelivered_queue.inspect_all_messages_for_key(key):
                    if session.accept_response(undelivered_message):
                        LOGGER.debug(
                            "Sending previously undelivered message via inbound session"
                        )
                        self.undelivered_queue.remove_message_for_key(
                            key, undelivered_message
                        )
