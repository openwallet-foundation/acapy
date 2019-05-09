"""
The Conductor.

The conductor is responsible for coordinating messages that are received
over the network, communicating with the ledger, passing messages to handlers,
instantiating concrete implementations of required modules and storing data in the
wallet.

"""

import logging

from typing import Coroutine, Union

from .admin.server import AdminServer
from .admin.service import AdminService
from .config.provider import CachedProvider, ClassProvider
from .dispatcher import Dispatcher
from .error import StartupError
from .logging import LoggingConfigurator
from .ledger.base import BaseLedger
from .ledger.provider import LedgerProvider
from .issuer.base import BaseIssuer
from .holder.base import BaseHolder
from .verifier.base import BaseVerifier
from .messaging.agent_message import AgentMessage
from .messaging.actionmenu.base_service import BaseMenuService
from .messaging.actionmenu.driver_service import DriverMenuService
from .messaging.connections.manager import ConnectionManager
from .messaging.connections.models.connection_target import ConnectionTarget
from .messaging.introduction.base_service import BaseIntroductionService
from .messaging.introduction.demo_service import DemoIntroductionService
from .messaging.message_factory import MessageFactory
from .messaging.request_context import RequestContext
from .storage.base import BaseStorage
from .storage.provider import StorageProvider
from .transport.inbound import InboundTransportConfiguration
from .transport.inbound.manager import InboundTransportManager
from .transport.outbound.manager import OutboundTransportManager
from .transport.outbound.queue.basic import BasicOutboundMessageQueue
from .wallet.base import BaseWallet
from .wallet.provider import WalletProvider
from .wallet.crypto import seed_to_did


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
        self.context = None
        self.connection_mgr = None
        self.dispatcher = Dispatcher()
        self.logger = logging.getLogger(__name__)
        self.message_factory = message_factory
        self.inbound_transport_configs = transport_configs
        self.outbound_transports = outbound_transports
        self.settings = settings.copy() if settings else {}
        self.init_context()

    def init_context(self):
        """Initialize the global request context."""

        context = RequestContext(settings=self.settings)
        context.settings.set_default("default_endpoint", "http://localhost:10000")
        context.settings.set_default("default_label", "Indy Catalyst Agent")

        context.injector.bind_instance(MessageFactory, self.message_factory)

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

        self.connection_mgr = ConnectionManager(context)
        context.injector.bind_instance(ConnectionManager, self.connection_mgr)

        self.context = context

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
                _connection, invitation = await self.connection_mgr.create_invitation()
                invite_url = invitation.to_url()
                print("Invitation URL:")
                print(invite_url)
            except Exception:
                self.logger.exception("Error sending invitation")

        # Auto-send an invitation to another agent
        send_invite_to = context.settings.get("debug.send_invitation_to")
        if send_invite_to:
            try:
                _connection, invitation = await self.connection_mgr.create_invitation()
                await self.connection_mgr.send_invitation(invitation, send_invite_to)
            except Exception:
                self.logger.exception("Error sending invitation")

    async def inbound_message_router(
        self,
        message_body: Union[str, bytes],
        transport_type: str,
        reply: Coroutine = None,
    ):
        """
        Route inbound messages.

        Args:
            message_body: Body of the incoming message
            transport_type: Type of transport this message came from
            reply: Function to reply to this message

        """
        try:
            context = await self.connection_mgr.expand_message(
                message_body, transport_type
            )
        except Exception:
            self.logger.exception("Error expanding message")
            raise

        result = await self.dispatcher.dispatch(
            context, self.outbound_message_router, reply
        )
        # TODO: need to use callback instead?
        #       respond immediately after message parse in case of req-res transport?
        return result.serialize() if result else None

    async def outbound_message_router(
        self, message: Union[AgentMessage, str, bytes], target: ConnectionTarget
    ) -> None:
        """
        Route an outbound message.

        Args:
            message: An agent message to be sent
            target: Target to send message to
        """
        payload = await self.connection_mgr.compact_message(message, target)
        await self.outbound_transport_manager.send_message(payload, target.endpoint)
