"""
The Conductor.

The conductor is responsible for coordinating messages that are received
over the network, communicating with the ledger, passing messages to handlers,
instantiating concrete implementations of required modules and storing data in the
wallet.

"""

import hashlib
import logging

from .admin.base_server import BaseAdminServer
from .admin.server import AdminServer
from .config.default_context import ContextBuilder
from .config.injection_context import InjectionContext
from .config.ledger import ledger_config
from .config.logging import LoggingConfigurator
from .config.wallet import wallet_config
from .dispatcher import Dispatcher
from .protocols.connections.manager import ConnectionManager, ConnectionManagerError
from .messaging.responder import BaseResponder
from .messaging.task_queue import CompletedTask, TaskQueue
from .stats import Collector
from .transport.inbound.manager import InboundTransportManager
from .transport.inbound.message import InboundMessage
from .transport.outbound.base import OutboundDeliveryError
from .transport.outbound.manager import OutboundTransportManager
from .transport.outbound.message import OutboundMessage
from .transport.wire_format import BaseWireFormat

LOGGER = logging.getLogger(__name__)


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
        self.inbound_transport_manager: InboundTransportManager = None
        self.outbound_transport_manager: OutboundTransportManager = None

    async def setup(self):
        """Initialize the global request context."""

        context = await self.context_builder.build()

        self.dispatcher = Dispatcher(context)

        wire_format = await context.inject(BaseWireFormat, required=False)
        if wire_format and hasattr(wire_format, "task_queue"):
            wire_format.task_queue = self.dispatcher.task_queue

        # Register all inbound transports
        self.inbound_transport_manager = InboundTransportManager(
            context, self.inbound_message_router, self.handle_not_returned,
        )
        await self.inbound_transport_manager.setup()

        # Register all outbound transports
        self.outbound_transport_manager = OutboundTransportManager(
            context, self.handle_not_delivered
        )
        await self.outbound_transport_manager.setup()

        # Admin API
        if context.settings.get("admin.enabled"):
            try:
                admin_host = context.settings.get("admin.host", "0.0.0.0")
                admin_port = context.settings.get("admin.port", "80")
                self.admin_server = AdminServer(
                    admin_host,
                    admin_port,
                    context,
                    self.outbound_message_router,
                    self.webhook_router,
                    self.dispatcher.task_queue,
                    self.get_stats,
                )
                webhook_urls = context.settings.get("admin.webhook_urls")
                if webhook_urls:
                    for url in webhook_urls:
                        self.admin_server.add_webhook_target(url)
                context.injector.bind_instance(BaseAdminServer, self.admin_server)
                if "http" not in self.outbound_transport_manager.registered_schemes:
                    self.outbound_transport_manager.register("http")
            except Exception:
                LOGGER.exception("Unable to register admin server")
                raise

        # Fetch stats collector, if any
        collector = await context.inject(Collector, required=False)
        if collector:
            # add stats to our own methods
            collector.wrap(
                self,
                (
                    # "inbound_message_router",
                    "outbound_message_router",
                    # "create_inbound_session",
                ),
            )
            collector.wrap(self.dispatcher, "handle_message")
            # at the class level (!) should not be performed multiple times
            collector.wrap(
                ConnectionManager,
                (
                    "get_connection_targets",
                    "fetch_did_document",
                    "find_inbound_connection",
                ),
            )

        self.context = context

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
            LOGGER.exception("Unable to start inbound transports")
            raise
        try:
            await self.outbound_transport_manager.start()
        except Exception:
            LOGGER.exception("Unable to start outbound transports")
            raise

        # Start up Admin server
        if self.admin_server:
            try:
                await self.admin_server.start()
            except Exception:
                LOGGER.exception("Unable to start administration API")
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
                LOGGER.exception("Error creating invitation")

    async def stop(self, timeout=1.0):
        """Stop the agent."""
        shutdown = TaskQueue()
        if self.admin_server:
            shutdown.run(self.admin_server.stop())
        if self.inbound_transport_manager:
            shutdown.run(self.inbound_transport_manager.stop())
        if self.outbound_transport_manager:
            shutdown.run(self.outbound_transport_manager.stop())
        await shutdown.complete(timeout)

    def inbound_message_router(
        self, message: InboundMessage, can_respond: bool = False
    ):
        """
        Route inbound messages.

        Args:
            message: The inbound message instance
            can_respond: If the session supports return routing

        """

        if message.receipt.direct_response_requested and not can_respond:
            LOGGER.warning(
                "Direct response requested, but not supported by transport: %s",
                message.transport_type,
            )

        # Note: at this point we could send the message to a shared queue
        # if this pod is too busy to process it

        self.dispatcher.queue_message(
            message,
            self.outbound_message_router,
            self.admin_server and self.admin_server.send_webhook,
            lambda completed: self.dispatch_complete(message, completed),
        )

    def dispatch_complete(self, message: InboundMessage, completed: CompletedTask):
        """Handle completion of message dispatch."""
        if completed.exc_info:
            LOGGER.exception(
                "Exception in message handler:", exc_info=completed.exc_info
            )
        self.inbound_transport_manager.dispatch_complete(message, completed)

    async def get_stats(self) -> dict:
        """Get the current stats tracked by the conductor."""
        stats = {
            "in_sessions": len(self.inbound_transport_manager.sessions),
            "out_encode": 0,
            "out_deliver": 0,
            "task_active": self.dispatcher.task_queue.current_active,
            "task_done": self.dispatcher.task_queue.total_done,
            "task_failed": self.dispatcher.task_queue.total_failed,
            "task_pending": self.dispatcher.task_queue.current_pending,
        }
        for m in self.outbound_transport_manager.outbound_buffer:
            if m.state == m.STATE_ENCODE:
                stats["out_encode"] += 1
            if m.state == m.STATE_DELIVER:
                stats["out_deliver"] += 1
        return stats

    async def outbound_message_router(
        self,
        context: InjectionContext,
        outbound: OutboundMessage,
        inbound: InboundMessage = None,
    ) -> None:
        """
        Route an outbound message.

        Args:
            context: The request context
            message: An outbound message to be sent
            inbound: The inbound message that produced this response, if available
        """
        if not outbound.target and outbound.reply_to_verkey:
            if not outbound.reply_from_verkey and inbound:
                outbound.reply_from_verkey = inbound.receipt.recipient_verkey
            # return message to an inbound session
            if self.inbound_transport_manager.return_to_session(outbound):
                return

        await self.queue_outbound(context, outbound, inbound)

    def handle_not_returned(self, context: InjectionContext, outbound: OutboundMessage):
        """Handle a message that failed delivery via an inbound session."""
        self.dispatcher.run_task(self.queue_outbound(context, outbound))

    async def queue_outbound(
        self,
        context: InjectionContext,
        outbound: OutboundMessage,
        inbound: InboundMessage = None,
    ):
        """
        Queue an outbound message.

        Args:
            context: The request context
            message: An outbound message to be sent
            inbound: The inbound message that produced this response, if available
        """
        # populate connection target(s)
        if not outbound.target and not outbound.target_list and outbound.connection_id:
            # using provided request context
            mgr = ConnectionManager(context)
            try:
                outbound.target_list = await self.dispatcher.run_task(
                    mgr.get_connection_targets(connection_id=outbound.connection_id)
                )
            except ConnectionManagerError:
                LOGGER.exception("Error preparing outbound message for transmission")
                return

        try:
            self.outbound_transport_manager.enqueue_message(context, outbound)
        except OutboundDeliveryError:
            LOGGER.warning("Cannot queue message for delivery, no supported transport")
            self.handle_not_delivered(context, outbound)

    def handle_not_delivered(
        self, context: InjectionContext, outbound: OutboundMessage
    ):
        """Handle a message that failed delivery via outbound transports."""
        self.inbound_transport_manager.return_undelivered(outbound)

    def webhook_router(
        self, topic: str, payload: dict, endpoint: str, retries: int = None
    ):
        """
        Route a webhook through the outbound transport manager.

        Args:
            topic: The webhook topic
            payload: The webhook payload
            endpoint: The endpoint of the webhook target
            retries: The number of retries
        """
        try:
            self.outbound_transport_manager.enqueue_webhook(
                topic, payload, endpoint, retries
            )
        except OutboundDeliveryError:
            LOGGER.warning(
                "Cannot queue message webhook for delivery, no supported transport"
            )
