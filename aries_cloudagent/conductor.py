"""
The Conductor.

The conductor is responsible for coordinating messages that are received
over the network, communicating with the ledger, passing messages to handlers,
instantiating concrete implementations of required modules and storing data in the
wallet.

"""

import asyncio
from collections import OrderedDict
import hashlib
import logging
from typing import Coroutine, Union

from .delivery_queue import DeliveryQueue
from .admin.base_server import BaseAdminServer
from .admin.server import AdminServer
from .config.default_context import ContextBuilder
from .config.injection_context import InjectionContext
from .config.ledger import ledger_config
from .config.logging import LoggingConfigurator
from .config.wallet import wallet_config
from .dispatcher import Dispatcher
from .protocols.connections.manager import ConnectionManager, ConnectionManagerError
from .connections.models.connection_record import ConnectionRecord
from .messaging.error import MessageParseError, MessagePrepareError
from .messaging.outbound_message import OutboundMessage
from .messaging.responder import BaseResponder
from .messaging.serializer import MessageSerializer
from .messaging.socket import SocketInfo, SocketRef
from .stats import Collector
from .storage.error import StorageNotFoundError
from .transport.inbound.base import InboundTransportConfiguration
from .transport.inbound.manager import InboundTransportManager
from .transport.outbound.manager import OutboundTransportManager
from .transport.outbound.queue.base import BaseOutboundMessageQueue


class Conductor:
    """
    Conductor class.

    Class responsible for initializing concrete implementations
    of our require interfaces and routing inbound and outbound message data.
    """

    def __init__(self, context_builder: ContextBuilder) -> None:
        """
        Initialize an instance of Conductor.

        Args:
            inbound_transports: Configuration for inbound transports
            outbound_transports: Configuration for outbound transports
            settings: Dictionary of various settings

        """
        self.admin_server = None
        self.context: InjectionContext = None
        self.context_builder = context_builder
        self.dispatcher: Dispatcher = None
        self.logger = logging.getLogger(__name__)
        self.message_serializer: MessageSerializer = None
        self.inbound_transport_manager: InboundTransportManager = None
        self.outbound_transport_manager: OutboundTransportManager = None
        self.sockets = OrderedDict()
        self.undelivered_queue: DeliveryQueue = None

    async def setup(self):
        """Initialize the global request context."""

        context = await self.context_builder.build()

        # Populate message serializer
        self.message_serializer = await context.inject(MessageSerializer)

        # Setup Delivery Queue
        if context.settings.get("queue.enable_undelivered_queue"):
            self.undelivered_queue = DeliveryQueue()

        # Register all inbound transports
        self.inbound_transport_manager = InboundTransportManager()
        inbound_transports = context.settings.get("transport.inbound_configs") or []
        for transport in inbound_transports:
            try:
                module, host, port = transport
                self.inbound_transport_manager.register(
                    InboundTransportConfiguration(module=module, host=host, port=port),
                    self.inbound_message_router,
                    self.register_socket,
                )
            except Exception:
                self.logger.exception("Unable to register inbound transport")
                raise

        # Fetch stats collector, if any
        collector = await context.inject(Collector, required=False)

        # Register all outbound transports
        outbound_queue = await context.inject(BaseOutboundMessageQueue)
        if collector:
            collector.wrap(outbound_queue, ("enqueue", "dequeue"))
        self.outbound_transport_manager = OutboundTransportManager(
            outbound_queue, collector
        )
        outbound_transports = context.settings.get("transport.outbound_configs") or []
        for outbound_transport in outbound_transports:
            try:
                self.outbound_transport_manager.register(outbound_transport)
            except Exception:
                self.logger.exception("Unable to register outbound transport")
                raise

        # Admin API
        if context.settings.get("admin.enabled"):
            try:
                admin_host = context.settings.get("admin.host", "0.0.0.0")
                admin_port = context.settings.get("admin.port", "80")
                self.admin_server = AdminServer(
                    admin_host, admin_port, context, self.outbound_message_router
                )
                webhook_urls = context.settings.get("admin.webhook_urls")
                if webhook_urls:
                    for url in webhook_urls:
                        self.admin_server.add_webhook_target(url)
                context.injector.bind_instance(BaseAdminServer, self.admin_server)
            except Exception:
                self.logger.exception("Unable to register admin server")
                raise

        self.context = context
        self.dispatcher = Dispatcher(self.context)

        if collector:
            # add stats to our own methods
            collector.wrap(
                self,
                (
                    "inbound_message_router",
                    "outbound_message_router",
                    "prepare_outbound_message",
                ),
            )
            collector.wrap(self.dispatcher, "dispatch")
            # at the class level (!) should not be performed multiple times
            collector.wrap(
                ConnectionManager,
                (
                    "get_connection_target",
                    "fetch_did_document",
                    "find_message_connection",
                ),
            )

    async def start(self) -> None:
        """Start the agent."""

        context = self.context

        # Configure the wallet
        public_did = await wallet_config(context)

        # Configure the ledger
        await ledger_config(context, public_did)

        # Start up transports
        try:
            await self.inbound_transport_manager.start()
        except Exception:
            self.logger.exception("Unable to start inbound transports")
            raise
        try:
            await self.outbound_transport_manager.start()
        except Exception:
            self.logger.exception("Unable to start outbound transports")
            raise

        # Start up Admin server
        if self.admin_server:
            try:
                await self.admin_server.start()
            except Exception:
                self.logger.exception("Unable to start administration API")
            # Make admin responder available during message parsing
            # This allows webhooks to be called when a connection is marked active,
            # for example
            context.injector.bind_instance(BaseResponder, self.admin_server.responder)

        # Get agent label
        default_label = context.settings.get("default_label")

        # Show some details about the configuration to the user
        LoggingConfigurator.print_banner(
            default_label,
            self.inbound_transport_manager.registered_transports,
            self.outbound_transport_manager.registered_transports,
            public_did,
            self.admin_server,
        )

        # Create a static connection for use by the test-suite
        if context.settings.get("debug.test_suite_endpoint"):
            mgr = ConnectionManager(self.context)
            their_endpoint = context.settings["debug.test_suite_endpoint"]
            test_conn = await mgr.create_static_connection(
                my_seed=hashlib.sha256(b"aries-protocol-test-subject").digest(),
                their_seed=hashlib.sha256(b"aries-protocol-test-suite").digest(),
                their_endpoint=their_endpoint,
                their_role="tester",
                alias="test-suite",
            )
            print("Created static connection for test suite")
            print(" - My DID:", test_conn.my_did)
            print(" - Their DID:", test_conn.their_did)
            print(" - Their endpoint:", their_endpoint)
            print()

        # Print an invitation to the terminal
        if context.settings.get("debug.print_invitation"):
            try:
                mgr = ConnectionManager(self.context)
                _connection, invitation = await mgr.create_invitation(
                    their_role=context.settings.get("debug.invite_role"),
                    my_label=context.settings.get("debug.invite_label"),
                    multi_use=context.settings.get("debug.invite_multi_use", False),
                    public=context.settings.get("debug.invite_public", False),
                )
                base_url = context.settings.get("invite_base_url")
                invite_url = invitation.to_url(base_url)
                print("Invitation URL:")
                print(invite_url)
            except Exception:
                self.logger.exception("Error creating invitation")

    async def stop(self, timeout=0.1):
        """Stop the agent."""
        tasks = []
        if self.admin_server:
            tasks.append(self.admin_server.stop())
        if self.inbound_transport_manager:
            tasks.append(self.inbound_transport_manager.stop())
        if self.outbound_transport_manager:
            tasks.append(self.outbound_transport_manager.stop())
        await asyncio.wait_for(asyncio.gather(*tasks), timeout)

    async def register_socket(
        self, *, handler: Coroutine = None, single_response: asyncio.Future = None
    ) -> SocketRef:
        """Register a new duplex connection."""
        socket = SocketInfo(handler=handler, single_response=single_response)
        socket_id = socket.socket_id
        self.sockets[socket_id] = socket

        async def close_socket():
            socket.closed = True

        return SocketRef(socket_id=socket_id, close=close_socket)

    async def inbound_message_router(
        self,
        message_body: Union[str, bytes],
        transport_type: str = None,
        socket_id: str = None,
        single_response: asyncio.Future = None,
    ) -> asyncio.Future:
        """
        Route inbound messages.

        Args:
            message_body: Body of the incoming message
            transport_type: Type of transport this message came from
            socket_id: The identifier of the incoming socket connection
            single_response: A future to contain the first direct response message

        """

        try:
            parsed_msg, delivery = await self.message_serializer.parse_message(
                self.context, message_body, transport_type
            )
        except MessageParseError:
            self.logger.exception("Error expanding message")
            raise

        connection_mgr = ConnectionManager(self.context)
        connection = await connection_mgr.find_message_connection(delivery)
        if connection:
            delivery.connection_id = connection.connection_id

        if single_response and not socket_id:
            # if transport wasn't a socket, make a virtual socket used for responses
            socket = SocketInfo(single_response=single_response)
            socket_id = socket.socket_id
            self.sockets[socket_id] = socket

        if socket_id:
            if socket_id not in self.sockets:
                self.logger.warning(
                    "Inbound message on unregistered socket ID: %s", socket_id
                )
                socket_id = None
            elif self.sockets[socket_id].closed:
                self.logger.warning(
                    "Inbound message on closed socket ID: %s", socket_id
                )
                socket_id = None

        delivery.socket_id = socket_id
        socket: SocketInfo = self.sockets[socket_id] if socket_id else None

        if socket:
            socket.process_incoming(parsed_msg, delivery)
        elif (
            delivery.direct_response_requested
            and delivery.direct_response_requested != SocketInfo.REPLY_MODE_NONE
        ):
            self.logger.warning(
                "Direct response requested, but not supported by transport: %s",
                delivery.transport_type,
            )

        handler_done = await self.dispatcher.dispatch(
            parsed_msg, delivery, connection, self.outbound_message_router
        )
        return asyncio.ensure_future(self.complete_dispatch(handler_done, socket))

    async def complete_dispatch(self, dispatch: asyncio.Future, socket: SocketInfo):
        """Wait for the dispatch to complete and perform final actions."""
        await dispatch
        await self.queue_processing(socket)
        if socket:
            socket.dispatch_complete()

    async def queue_processing(self, socket: SocketInfo):
        """
        Interact with undelivered queue to find applicable messages.

        Args:
            socket: The incoming socket connection
        """
        if (
            socket
            and socket.reply_mode
            and not socket.closed
            and self.undelivered_queue
        ):
            for key in socket.reply_verkeys:
                if not isinstance(key, str):
                    key = key.value
                if self.undelivered_queue.has_message_for_key(key):
                    for (
                        undelivered_message
                    ) in self.undelivered_queue.inspect_all_messages_for_key(key):
                        # pending message. Transmit, then kill single_response
                        if socket.select_outgoing(undelivered_message):
                            self.logger.debug(
                                "Sending Queued Message via inbound connection"
                            )
                            self.undelivered_queue.remove_message_for_key(
                                key, undelivered_message
                            )
                            await socket.send(undelivered_message)

    async def get_connection_target(
        self, connection_id: str, context: InjectionContext = None
    ):
        """Get a `ConnectionTarget` instance representing a connection.

        Args:
            connection_id: The connection record identifier
            context: An optional injection context
        """

        context = context or self.context

        try:
            record = await ConnectionRecord.retrieve_by_id(context, connection_id)
        except StorageNotFoundError as e:
            raise MessagePrepareError(
                "Could not locate connection record: {}".format(connection_id)
            ) from e
        mgr = ConnectionManager(context)
        try:
            target = await mgr.get_connection_target(record)
        except ConnectionManagerError as e:
            raise MessagePrepareError(str(e)) from e
        if not target:
            raise MessagePrepareError(
                "No target found for connection: {}".format(connection_id)
            )
        return target

    async def prepare_outbound_message(
        self,
        message: OutboundMessage,
        context: InjectionContext = None,
        direct_response: bool = False,
    ):
        """Prepare a response message for transmission.

        Args:
            message: An outbound message to be sent
            context: Optional request context
            direct_response: Skip wrapping the response in forward messages
        """

        context = context or self.context

        if message.connection_id and not message.target:
            message.target = await self.get_connection_target(message.connection_id)

        if not message.encoded and message.target:
            target = message.target
            message.payload = await self.message_serializer.encode_message(
                context,
                message.payload,
                target.recipient_keys or [],
                (not direct_response) and target.routing_keys or [],
                target.sender_key,
            )
            message.encoded = True

    async def outbound_message_router(
        self, message: OutboundMessage, context: InjectionContext = None
    ) -> None:
        """
        Route an outbound message.

        Args:
            message: An outbound message to be sent
            context: Optional request context
        """

        # try socket connections first, preferring the same socket ID
        socket_id = message.reply_socket_id
        sel_socket = None
        if (
            socket_id
            and socket_id in self.sockets
            and self.sockets[socket_id].select_outgoing(message)
        ):
            sel_socket = self.sockets[socket_id]
        else:
            for socket in self.sockets.values():
                if socket.select_outgoing(message):
                    sel_socket = socket
                    break
        if sel_socket:
            try:
                await self.prepare_outbound_message(message, context, True)
            except MessagePrepareError:
                self.logger.exception(
                    "Error preparing outbound message for direct response"
                )
                return

            await sel_socket.send(message)
            self.logger.debug("Returned message to socket %s", sel_socket.socket_id)
            return

        try:
            await self.prepare_outbound_message(message, context)
        except MessagePrepareError:
            self.logger.exception("Error preparing outbound message for transmission")
            return

        # deliver directly to endpoint
        if message.endpoint:
            await self.outbound_transport_manager.send_message(message)
            return

        # Add message to outbound queue, indexed by key
        if self.undelivered_queue:
            self.undelivered_queue.add_message(message)
