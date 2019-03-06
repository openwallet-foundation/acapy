"""
The Conductor.

The conductor is responsible for coordinating messages that are received
over the network, communicating with the ledger, passing messages to handlers,
instantiating concrete implementations of required modules and storing data in the
wallet.

"""

import logging

from typing import Coroutine, Union

from .admin.manager import AdminManager
from .admin.server import AdminServer
from .classloader import ClassLoader
from .dispatcher import Dispatcher
from .error import BaseError
from .logging import LoggingConfigurator
from .messaging.agent_message import AgentMessage
from .messaging.connections.manager import ConnectionManager
from .messaging.connections.models.connection_target import ConnectionTarget
from .messaging.message_factory import MessageFactory
from .messaging.request_context import RequestContext
from .transport.inbound import InboundTransportConfiguration
from .transport.inbound.manager import InboundTransportManager
from .transport.outbound.manager import OutboundTransportManager
from .transport.outbound.queue.basic import BasicOutboundMessageQueue


class ConductorError(BaseError):
    """Conductor error."""


class Conductor:
    """
    Conductor class.

    Class responsible for initalizing concrete implementations
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

        wallet_type = self.settings.get("wallet.type", "basic").lower()
        wallet_type = self.WALLET_TYPES.get(wallet_type, wallet_type)
        wallet_cfg = {}
        if "wallet.key" in self.settings:
            wallet_cfg["key"] = self.settings["wallet.key"]
        if "wallet.name" in self.settings:
            wallet_cfg["name"] = self.settings["wallet.name"]
        context.wallet = ClassLoader.load_class(wallet_type)(wallet_cfg)

        storage_type = self.settings.get("storage.type", "basic").lower()
        storage_type = self.STORAGE_TYPES.get(storage_type, storage_type)
        context.storage = ClassLoader.load_class(storage_type)(context.wallet)

        self.context = context
        self.connection_mgr = ConnectionManager(context)
        self.dispatcher = Dispatcher()

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
                AdminManager.SERVER = self.admin_server
            except Exception:
                self.logger.exception("Unable to start administration API")

        # Show some details about the configuration to the user
        LoggingConfigurator.print_banner(
            self.inbound_transport_manager.transports,
            self.outbound_transport_manager.registered_transports,
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
