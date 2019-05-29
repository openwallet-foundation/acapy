"""
The Conductor.

The conductor is responsible for coordinating messages that are received
over the network, communicating with the ledger, passing messages to handlers,
instantiating concrete implementations of required modules and storing data in the
wallet.

"""

import asyncio
from collections import OrderedDict
import logging
from typing import Coroutine, Sequence, Union
import uuid

from .admin.server import AdminServer
from .admin.service import AdminService
from .config.injection_context import InjectionContext
from .config.provider import CachedProvider, ClassProvider
from .dispatcher import Dispatcher
from .error import StartupError
from .logging import LoggingConfigurator
from .ledger.base import BaseLedger
from .ledger.provider import LedgerProvider
from .issuer.base import BaseIssuer
from .holder.base import BaseHolder
from .verifier.base import BaseVerifier
from .messaging.actionmenu.base_service import BaseMenuService
from .messaging.actionmenu.driver_service import DriverMenuService
from .messaging.connections.manager import ConnectionManager, ConnectionManagerError
from .messaging.connections.models.connection_record import ConnectionRecord
from .messaging.error import MessageParseError, MessagePrepareError
from .messaging.introduction.base_service import BaseIntroductionService
from .messaging.introduction.demo_service import DemoIntroductionService
from .messaging.message_delivery import MessageDelivery
from .messaging.message_factory import MessageFactory
from .messaging.outbound_message import OutboundMessage
from .messaging.request_context import RequestContext
from .messaging.serializer import MessageSerializer
from .storage.base import BaseStorage
from .storage.error import StorageNotFoundError
from .storage.provider import StorageProvider
from .transport.inbound import InboundTransportConfiguration
from .transport.inbound.manager import InboundTransportManager
from .transport.outbound.manager import OutboundTransportManager
from .transport.outbound.queue.basic import BasicOutboundMessageQueue
from .wallet.base import BaseWallet
from .wallet.provider import WalletProvider
from .wallet.crypto import seed_to_did


class SocketInfo:
    """Track an open transport connection for direct routing of outbound messages."""

    REPLY_MODE_ALL = "all"
    REPLY_MODE_NONE = "none"
    REPLY_MODE_THREAD = "thread"

    def __init__(
        self,
        *,
        connection_id: str = None,
        handler: Coroutine = None,
        reply_mode: str = None,
        reply_thread_ids: Sequence[str] = None,
        reply_verkeys: Sequence[str] = None,
        single_response: asyncio.Future = None,
        socket_id: str = None,
    ):
        """Initialize the socket info."""
        self._closed = False
        self.connection_id = connection_id
        self.handler = handler
        self.reply_thread_ids = set(reply_thread_ids) if reply_thread_ids else set()
        self.reply_verkeys = set(reply_verkeys) if reply_verkeys else set()
        self.single_response = single_response
        self.socket_id = socket_id or str(uuid.uuid4())
        # calls setter
        self._reply_mode = None
        self.reply_mode = reply_mode

    @property
    def closed(self) -> bool:
        """Accessor for the socket closed state."""
        if self._closed:
            return True
        if self.single_response and self.single_response.done():
            self._closed = True
            return True
        return False

    @closed.setter
    def closed(self, flag: bool):
        """Setter for the socket closed state."""
        self._closed = flag

    @property
    def reply_mode(self) -> str:
        """Accessor for the socket reply mode."""
        return self._reply_mode

    @reply_mode.setter
    def reply_mode(self, mode: str):
        """Setter for the socket reply mode."""
        if mode != self.REPLY_MODE_THREAD:
            if mode != self.REPLY_MODE_ALL:
                mode = None
            # reset the tracked thread IDs when the mode is changed to all or none
            self.reply_thread_ids = set()
        self._reply_mode = mode

    def add_reply_thread_id(self, thid: str):
        """Add a thread ID to the set of potential reply targets."""
        if thid:
            self.reply_thread_ids.add(thid)

    def add_reply_verkey(self, verkey: str):
        """Add a verkey to the set of potential reply targets."""
        if verkey:
            self.reply_verkeys.add(verkey)

    def process_incoming(self, parsed_msg: dict, delivery: MessageDelivery):
        """."""
        mode = self.reply_mode = delivery.direct_response_requested
        self.add_reply_verkey(delivery.sender_verkey)
        if mode == self.REPLY_MODE_THREAD:
            self.add_reply_thread_id(delivery.thread_id)
        delivery.direct_response = bool(mode)

    def dispatch_complete(self):
        """."""
        if not self.closed and self.single_response:
            self.single_response.cancel()

    def select_outgoing(self, message: OutboundMessage) -> bool:
        """."""
        mode = self.reply_mode
        if not self.closed:
            if (
                mode == self.REPLY_MODE_ALL
                and message.reply_socket_id == self.socket_id
            ):
                return True
            if (
                mode == self.REPLY_MODE_ALL
                and message.reply_to_verkey
                and message.reply_to_verkey in self.reply_verkeys
            ):
                return True
            if (
                mode == self.REPLY_MODE_THREAD
                and message.reply_thread_id
                and message.reply_thread_id in self.reply_thread_ids
            ):
                return True
        return False

    async def send(self, message: OutboundMessage):
        """."""
        if self.single_response:
            self.single_response.set_result(message.payload)
        elif self.handler:
            await self.handler(message.payload)


class Conductor:
    """
    Conductor class.

    Class responsible for initializing concrete implementations
    of our require interfaces and routing inbound and outbound message data.
    """

    def __init__(
        self,
        transport_configs: InboundTransportConfiguration,
        outbound_transports,
        message_factory: MessageFactory,
        settings: dict,
    ) -> None:
        """
        Initialize an instance of Conductor.

        Args:
            transport_configs: Configuration for inbound transport
            outbound_transports: Configuration for outbound transport
            message_factory: Message factory for discovering and deserializing messages
            settings: Dictionary of various settings

        """
        self.admin_server = None
        self.context: RequestContext = None
        self.dispatcher: Dispatcher = None
        self.logger = logging.getLogger(__name__)
        self.message_factory = message_factory
        self.message_serializer: MessageSerializer = MessageSerializer()
        self.inbound_transport_configs = transport_configs
        self.outbound_transports = outbound_transports
        self.settings = settings.copy() if settings else {}
        self.sockets = OrderedDict()
        self.init_context()

    def init_context(self):
        """Initialize the global request context."""

        context = RequestContext(settings=self.settings)
        context.settings.set_default("default_label", "Indy Catalyst Agent")

        context.injector.bind_instance(MessageFactory, self.message_factory)
        context.injector.bind_instance(MessageSerializer, self.message_serializer)

        context.injector.bind_provider(BaseStorage, CachedProvider(StorageProvider()))
        context.injector.bind_provider(BaseWallet, CachedProvider(WalletProvider()))

        context.injector.bind_provider(BaseLedger, CachedProvider(LedgerProvider()))
        context.injector.bind_provider(
            BaseIssuer,
            ClassProvider(
                "indy_catalyst_agent.issuer.indy.IndyIssuer",
                ClassProvider.Inject(BaseWallet),
            ),
        )
        context.injector.bind_provider(
            BaseHolder,
            ClassProvider(
                "indy_catalyst_agent.holder.indy.IndyHolder",
                ClassProvider.Inject(BaseWallet),
            ),
        )
        context.injector.bind_provider(
            BaseVerifier,
            ClassProvider(
                "indy_catalyst_agent.verifier.indy.IndyVerifier",
                ClassProvider.Inject(BaseWallet),
            ),
        )

        # Allow action menu to be provided by driver
        context.injector.bind_instance(BaseMenuService, DriverMenuService(context))
        context.injector.bind_instance(
            BaseIntroductionService, DemoIntroductionService(context)
        )

        # Admin API
        if context.settings.get("admin.enabled"):
            try:
                admin_host = context.settings.get("admin.host", "0.0.0.0")
                admin_port = context.settings.get("admin.port", "80")
                self.admin_server = AdminServer(
                    admin_host, admin_port, context, self.outbound_message_router
                )
                context.injector.bind_instance(AdminServer, self.admin_server)
            except Exception:
                self.logger.exception("Unable to initialize administration API")

        self.context = context
        self.dispatcher = Dispatcher(self.context)

    async def start(self) -> None:
        """Start the agent."""

        context = self.context

        wallet: BaseWallet = await context.inject(BaseWallet)

        wallet_seed = context.settings.get("wallet.seed")
        public_did_info = await wallet.get_public_did()
        public_did = None
        if public_did_info:
            public_did = public_did_info.did
            # If we already have a registered public did and it doesn't match
            # the one derived from `wallet_seed` then we error out.
            # TODO: Add a command to change public did explicitly
            if seed_to_did(wallet_seed) != public_did_info.did:
                raise StartupError(
                    "New seed provided which doesn't match the registered"
                    + f" public did {public_did_info.did}"
                )
        elif wallet_seed:
            public_did_info = await wallet.create_public_did(seed=wallet_seed)
            public_did = public_did_info.did

        # Register all inbound transports
        self.inbound_transport_manager = InboundTransportManager()
        for inbound_transport_config in self.inbound_transport_configs:
            module = inbound_transport_config.module
            host = inbound_transport_config.host
            port = inbound_transport_config.port

            self.inbound_transport_manager.register(
                module, host, port, self.inbound_message_router
            )

        await self.inbound_transport_manager.start_all()

        # TODO: Set queue driver dynamically via cli args
        queue = BasicOutboundMessageQueue
        self.outbound_transport_manager = OutboundTransportManager(queue)
        for outbound_transport in self.outbound_transports:
            try:
                self.outbound_transport_manager.register(outbound_transport)
            except Exception:
                self.logger.exception("Unable to register outbound transport")

        await self.outbound_transport_manager.start_all()

        # Admin API
        if self.admin_server:
            try:
                await self.admin_server.start()
                context.injector.bind_instance(
                    AdminService, AdminService(self.admin_server)
                )
            except Exception:
                self.logger.exception("Unable to start administration API")

        # Show some details about the configuration to the user
        LoggingConfigurator.print_banner(
            self.inbound_transport_manager.transports,
            self.outbound_transport_manager.registered_transports,
            public_did,
            self.admin_server,
        )

        # Debug settings
        test_seed = context.settings.get("debug.seed")
        if context.settings.get("debug.enabled"):
            if not test_seed:
                test_seed = "testseed000000000000000000000001"
        if test_seed:
            await wallet.create_local_did(test_seed)

        # Print an invitation to the terminal
        if context.settings.get("debug.print_invitation"):
            try:
                mgr = ConnectionManager(self.context)
                _connection, invitation = await mgr.create_invitation()
                invite_url = invitation.to_url()
                print("Invitation URL:")
                print(invite_url)
            except Exception:
                self.logger.exception("Error sending invitation")

        # Auto-send an invitation to another agent
        send_invite_to = context.settings.get("debug.send_invitation_to")
        if send_invite_to:
            try:
                mgr = ConnectionManager(self.context)
                _connection, invitation = await mgr.create_invitation()
                await mgr.send_invitation(invitation, send_invite_to)
            except Exception:
                self.logger.exception("Error sending invitation")

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

        if single_response and not socket_id:
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
        socket = self.sockets[socket_id] if socket_id else None

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

        future = await self.dispatcher.dispatch(
            parsed_msg, delivery, self.outbound_message_router
        )
        if socket:
            future.add_done_callback(lambda fut: socket.dispatch_complete())
        return future

    async def prepare_outbound_message(
        self, message: OutboundMessage, context: InjectionContext = None
    ):
        """Prepare a response message for transmission.

        Args:
            message: An outbound message to be sent
            context: Optional request context
        """

        context = context or self.context

        if not message.target:
            if message.connection_id:
                try:
                    record = await ConnectionRecord.retrieve_by_id(
                        context, message.connection_id
                    )
                except StorageNotFoundError as e:
                    raise MessagePrepareError(
                        "Could not locate connection record: {}".format(
                            message.connection_id
                        )
                    ) from e
                mgr = ConnectionManager(context)
                try:
                    target = await mgr.get_connection_target(record)
                except ConnectionManagerError as e:
                    raise MessagePrepareError(str(e)) from e
                if not target:
                    raise MessagePrepareError(
                        "No connection target for message: {}".format(
                            message.connection_id
                        )
                    )
                message.target = target

        if not message.encoded and message.target:
            target = message.target
            message.payload = await self.message_serializer.encode_message(
                context,
                message.payload,
                target.recipient_keys,
                target.routing_keys,
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
        try:
            await self.prepare_outbound_message(message, context)
        except MessagePrepareError:
            self.logger.exception("Error preparing outbound message for transmission")
            return

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
            await sel_socket.send(message)
            self.logger.debug("Returned message to socket %s", sel_socket.socket_id)
            return

        # deliver directly to endpoint
        if message.endpoint:
            await self.outbound_transport_manager.send_message(
                message.payload, message.endpoint
            )
            return

        self.logger.warning("No endpoint or direct route for outbound message, dropped")
