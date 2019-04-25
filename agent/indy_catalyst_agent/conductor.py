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
from .classloader import ClassLoader
from .dispatcher import Dispatcher
from .error import StartupError
from .logging import LoggingConfigurator
from .ledger.indy import IndyLedger
from .issuer.indy import IndyIssuer
from .holder.indy import IndyHolder
from .verifier.indy import IndyVerifier
from .messaging.agent_message import AgentMessage
from .messaging.actionmenu.driver_service import DriverMenuService
from .messaging.connections.manager import ConnectionManager
from .messaging.connections.models.connection_target import ConnectionTarget
from .messaging.introduction.demo_service import DemoIntroductionService
from .messaging.message_factory import MessageFactory
from .messaging.request_context import RequestContext
from .service.factory import ServiceRegistry
from .transport.inbound import InboundTransportConfiguration
from .transport.inbound.manager import InboundTransportManager
from .transport.outbound.manager import OutboundTransportManager
from .transport.outbound.queue.basic import BasicOutboundMessageQueue
from .wallet.crypto import seed_to_did


class Conductor:
    """
    Conductor class.

    Class responsible for initializing concrete implementations
    of our require interfaces and routing inbound and outbound message data.
    """

    STORAGE_TYPES = {
        "basic": "indy_catalyst_agent.storage.basic.BasicStorage",
        "indy": "indy_catalyst_agent.storage.indy.IndyStorage",
    }
    WALLET_TYPES = {
        "basic": "indy_catalyst_agent.wallet.basic.BasicWallet",
        "indy": "indy_catalyst_agent.wallet.indy.IndyWallet",
    }

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
        self.logger = logging.getLogger(__name__)
        self.message_factory = message_factory
        self.inbound_transport_configs = transport_configs
        self.outbound_transports = outbound_transports
        self.service_registry = None
        self.settings = settings.copy() if settings else {}

    async def start(self) -> None:
        """Start the agent."""
        context = RequestContext()
        context.default_endpoint = self.settings.get(
            "default_endpoint", "http://localhost:10001"
        )
        context.default_label = self.settings.get(
            "default_label", "Indy Catalyst Agent"
        )
        context.message_factory = self.message_factory
        context.settings = self.settings

        wallet_type = self.settings.get("wallet.type", "basic").lower()
        wallet_type = self.WALLET_TYPES.get(wallet_type, wallet_type)

        self.logger.info(wallet_type)

        wallet_cfg = {}
        if "wallet.key" in self.settings:
            wallet_cfg["key"] = self.settings["wallet.key"]
        if "wallet.name" in self.settings:
            wallet_cfg["name"] = self.settings["wallet.name"]
        context.wallet = ClassLoader.load_class(wallet_type)(wallet_cfg)
        await context.wallet.open()

        wallet_seed = self.settings.get("wallet.seed")
        public_did = None
        if wallet_seed:
            public_did_info = await context.wallet.get_public_did()

            # If we already have a registered public did and it doesn't match
            # the one derived from `wallet_seed` then we error out.
            # TODO: Add a command to change public did explicitly
            if public_did_info and seed_to_did(wallet_seed) != public_did_info.did:
                raise StartupError(
                    "New seed provided which doesn't match the registered"
                    + f" public did {public_did_info.did}"
                )

            if not public_did_info:
                public_did_info = await context.wallet.create_public_did(seed=wallet_seed)
                
            public_did = public_did_info.did

        # TODO: Load ledger implementation from command line args
        genesis_transactions = self.settings.get("ledger.genesis_transactions")
        if genesis_transactions:
            context.ledger = IndyLedger("default", context.wallet, genesis_transactions)

        # TODO: Load issuer implementation from command line args
        context.issuer = IndyIssuer(context.wallet)

        # TODO: Load holder implementation from command line args
        context.holder = IndyHolder(context.wallet)

        # TODO: Load holder implementation from command line args
        context.verifier = IndyVerifier(context.wallet)

        storage_default_type = "indy" if wallet_type == "indy" else "basic"
        storage_type = self.settings.get("storage.type", storage_default_type).lower()
        storage_type = self.STORAGE_TYPES.get(storage_type, storage_type)
        context.storage = ClassLoader.load_class(storage_type)(context.wallet)

        self.context = context
        self.connection_mgr = ConnectionManager(context)
        self.dispatcher = Dispatcher()
        self.service_registry = ServiceRegistry[RequestContext]()
        # Replaced in expand_message when context is cloned
        context.service_factory = self.service_registry.get_factory(context)

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
        if self.settings.get("admin.enabled"):
            try:
                admin_host = self.settings.get("admin.host", "0.0.0.0")
                admin_port = self.settings.get("admin.port", "80")
                self.admin_server = AdminServer(
                    admin_host, admin_port, context, self.outbound_message_router
                )
                await self.admin_server.start()
                self.service_registry.register_service_handler(
                    "admin", AdminService.service_handler(self.admin_server)
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
        test_seed = self.settings.get("debug.seed")
        if self.settings.get("debug.enabled"):
            if not test_seed:
                test_seed = "testseed000000000000000000000001"
        if test_seed:
            await context.wallet.create_local_did(test_seed)

        # Print an invitation to the terminal
        if self.settings.get("debug.print_invitation"):
            try:
                _connection, invitation = await self.connection_mgr.create_invitation()
                invite_url = invitation.to_url()
                print("Invitation URL:")
                print(invite_url)
            except Exception:
                self.logger.exception("Error sending invitation")

        # Auto-send an invitation to another agent
        send_invite_to = self.settings.get("debug.send_invitation_to")
        if send_invite_to:
            try:
                _connection, invitation = await self.connection_mgr.create_invitation()
                await self.connection_mgr.send_invitation(invitation, send_invite_to)
            except Exception:
                self.logger.exception("Error sending invitation")

        # Allow action menu to be provided by driver
        self.service_registry.register_service_handler(
            "actionmenu", DriverMenuService.service_handler()
        )
        self.service_registry.register_service_handler(
            "introduction", DemoIntroductionService.service_handler()
        )

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
                message_body, transport_type, self.service_registry.get_factory
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
