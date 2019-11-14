"""
The Conductor.

The conductor is responsible for coordinating messages that are received
over the network, communicating with the ledger, passing messages to handlers,
instantiating concrete implementations of required modules and storing data in the
wallet.

"""

import asyncio
import hashlib
import logging
import time
import uuid
from collections import OrderedDict
from typing import Callable, Coroutine, Union

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
from .messaging.responder import BaseResponder
from .stats import Collector
from .transport.base import BaseWireFormat
from .transport.pack_format import PackWireFormat
from .transport.inbound.base import InboundTransportConfiguration
from .transport.inbound.manager import InboundTransportManager
from .transport.inbound.message import InboundMessage
from .transport.inbound.session import InboundSession
from .transport.outbound.manager import OutboundTransportManager
from .transport.outbound.message import OutboundMessage
from .transport.queue.base import BaseMessageQueue
from .transport.queue.basic import BasicMessageQueue

LOGGER = logging.getLogger(__name__)


class TaskRunner:
    def __init__(self, *, max_pending: int = None):
        self.limiter = asyncio.Semaphore(max_pending) if max_pending else None
        self.max_pending = max_pending
        self.tasks = []

    def start_task(
        self, coro: Coroutine, on_complete: Callable = None, limited: bool = False
    ):
        task = asyncio.get_event_loop().create_task(coro)
        self.tasks.append(task)
        task.add_done_callback(
            lambda fut: self.completed_task(task, on_complete, limited)
        )
        return task

    async def start_limited(self, coro: Coroutine, on_complete: Callable = None):
        if self.limiter:
            await self.limiter.acquire()
        task = self.start_task(coro, on_complete, True)
        return task

    def completed_task(self, task: asyncio.Task, on_complete: Callable, limited: bool):
        """Wait for the dispatch to complete and perform final actions."""
        if task.exception():
            exc_val = task.exception()
            exc_info = type(exc_val), exc_val, task.get_stack()
            if not on_complete:
                LOGGER.exception("Error running task", exc_info=exc_info)
        else:
            exc_info = None
        self.tasks.remove(task)
        if limited and self.limiter:
            self.limiter.release()
        if on_complete:
            on_complete(task, exc_info)

    def cancel(self):
        for task in self.tasks:
            task.cancel()

    async def __await__(self):
        return await asyncio.gather(*self.tasks)

    async def wait_for(self, timeout: float):
        return await asyncio.wait_for(self, timeout)


class QueuedOutboundMessage:
    STATE_NEW = "new"
    STATE_PENDING = "pending"
    STATE_ENCODE = "encode"
    STATE_DELIVER = "deliver"
    STATE_RETRY = "retry"
    STATE_DONE = "done"

    def __init__(
        self,
        context: InjectionContext,
        message: OutboundMessage,
        target,
        transport_id: str,
    ):
        self.context = context
        self.delivery_task: asyncio.Task = None
        self.endpoint = target and target.endpoint
        self.error: Exception = None
        self.message = message
        self.payload: Union[str, bytes] = None
        self.retries = 0
        self.retry_at: float = None
        self.state = self.STATE_NEW
        self.target = target
        self.transport_id: str = transport_id


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
        self.dispatch_runner: TaskRunner = None
        self.inbound_queue: BaseMessageQueue = None
        self.inbound_sessions = OrderedDict()
        self.inbound_session_limit: asyncio.Semaphore = None
        self.inbound_transport_manager: InboundTransportManager = None
        self.outbound_buffer = []
        self.outbound_event: asyncio.Event = None
        self.outbound_new = []
        self.outbound_transport_manager: OutboundTransportManager = None
        self.runner: TaskRunner = None
        self.undelivered_queue: DeliveryQueue = None

    async def setup(self):
        """Initialize the global request context."""

        context = await self.context_builder.build()

        # Setup Delivery Queue
        if context.settings.get("queue.enable_undelivered_queue"):
            self.undelivered_queue = DeliveryQueue()

        # FIXME add config options
        self.outbound_event = asyncio.Event()
        self.inbound_session_limit = asyncio.Semaphore(50)
        self.inbound_queue = BasicMessageQueue()
        self.runner = TaskRunner(max_pending=50)
        self.dispatch_runner = TaskRunner(max_pending=50)

        # Register all inbound transports
        self.inbound_transport_manager = InboundTransportManager()
        inbound_transports = context.settings.get("transport.inbound_configs") or []
        for transport in inbound_transports:
            try:
                module, host, port = transport
                self.inbound_transport_manager.register(
                    InboundTransportConfiguration(module=module, host=host, port=port),
                    self.create_inbound_session,
                )
            except Exception:
                LOGGER.exception("Unable to register inbound transport")
                raise

        # Fetch stats collector, if any
        collector = await context.inject(Collector, required=False)

        # Register all outbound transports
        self.outbound_transport_manager = OutboundTransportManager(collector)
        outbound_transports = context.settings.get("transport.outbound_configs") or []
        for outbound_transport in outbound_transports:
            try:
                self.outbound_transport_manager.register(outbound_transport)
            except Exception:
                LOGGER.exception("Unable to register outbound transport")
                raise

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
                    self.runner.start_limited,
                )
                webhook_urls = context.settings.get("admin.webhook_urls")
                if webhook_urls:
                    for url in webhook_urls:
                        self.admin_server.add_webhook_target(url)
                context.injector.bind_instance(BaseAdminServer, self.admin_server)
            except Exception:
                LOGGER.exception("Unable to register admin server")
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
                    "create_inbound_session",
                ),
            )
            collector.wrap(self.dispatcher, "dispatch")
            # at the class level (!) should not be performed multiple times
            collector.wrap(
                ConnectionManager,
                (
                    "get_connection_targets",
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
            LOGGER.exception("Unable to start inbound transports")
            raise
        try:
            await self.outbound_transport_manager.start()
        except Exception:
            LOGGER.exception("Unable to start outbound transports")
            raise

        loop = asyncio.get_event_loop()
        loop.create_task(self.process_inbound())
        loop.create_task(self.process_outbound())
        # loop.create_task(self.log_status())

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
            self.outbound_transport_manager.registered_transports.values(),
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

    async def stop(self, timeout=0.1):
        """Stop the agent."""
        shutdown = TaskRunner()
        if self.admin_server:
            shutdown.start_task(self.admin_server.stop())
        if self.inbound_transport_manager:
            shutdown.start_task(self.inbound_transport_manager.stop())
        if self.outbound_transport_manager:
            shutdown.start_task(self.outbound_transport_manager.stop())
        await shutdown.wait_for(timeout)

    async def create_inbound_session(
        self,
        transport_type: str,
        client_info: dict = None,
        wire_format: BaseWireFormat = None,
    ):
        """Create a new inbound session."""
        await self.inbound_session_limit
        session = InboundSession(
            context=self.context,
            client_info=client_info,
            close_handler=self.closed_inbound_session,
            inbound_handler=self.inbound_message_router,
            session_id=str(uuid.uuid4()),
            transport_type=transport_type,
            wire_format=wire_format or PackWireFormat(),
        )
        self.inbound_sessions[session.session_id] = session
        return session

    def closed_inbound_session(self, session: InboundSession):
        """Clean up a closed session."""
        if session.session_id in self.inbound_sessions:
            del self.inbound_sessions[session.session_id]
            self.inbound_session_limit.release()
        # FIXME if there is a message in the buffer, re-queue it

    async def inbound_message_router(self, message: InboundMessage):
        """
        Route inbound messages.

        Args:
            message: The inbound message instance

        """

        if (
            message.receipt.direct_response_requested
            and message.receipt.direct_response_requested
            != InboundSession.REPLY_MODE_NONE
        ):
            LOGGER.warning(
                "Direct response requested, but not supported by transport: %s",
                message.transport_type,
            )

        # Note: at this point we could send the message to a shared queue
        # if this pod is too busy to process it

        # session = self.inbound_sessions.get(message.session_id)
        # print("receive inbound", session.client_info)
        await self.inbound_queue.enqueue(message)

    async def log_status(self):
        while True:
            await asyncio.sleep(5.0)
            e = 0
            p = 0
            t = 0
            for m in self.outbound_buffer:
                if m.state == m.STATE_ENCODE:
                    e += 1
                if m.state == m.STATE_DELIVER:
                    p += 1
                t += 1
            s = len(self.inbound_sessions)
            d = len(self.runner.tasks)
            print(f"{s:>4} sess  {d:>4} task  {e:>4} pack  {p:>4} send  {t:>4} out")

    async def process_inbound(self):
        """Continually watch the inbound queue and send to the dispatcher."""

        def complete(task, exc_info=None):
            # await self.queue_processing(socket)
            session = self.inbound_sessions.get(message.session_id)
            if session:
                # need to scan the outbound buffer and see if anything is queued
                # for this session first
                session.dispatch_complete(message)

        async for message in self.inbound_queue:
            await self.runner.start_limited(
                self.dispatcher.dispatch(message, self.outbound_message_router),
                complete,
            )

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

    def select_inbound_session(self, outbound: OutboundMessage):
        # if outbound.reply_session_id:

        # if inbound and inbound.receipt.

        #  if the message has multiple targets, we cannot direct return unless
        #  one of the targets has keys that match the inbound message (!)
        # if an

        accepted = False

        # try open inbound sessions first, preferring the same session ID
        # FIXME if outbound target is set, need to compare to inbound keys

        if not outbound.target:
            inbound_session = self.inbound_sessions.get(outbound.reply_session_id)
            if inbound_session:
                accepted, retry = inbound_session.accept_response(outbound)

            if not accepted:
                for inbound_session in self.inbound_sessions.values():
                    if inbound_session.session_id != outbound.reply_session_id:
                        accepted, retry = inbound_session.accept_response(outbound)
                        break

        if accepted:
            LOGGER.debug("Returned message to socket %s", inbound_session.session_id)

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

        # if inbound and inbound.direct_response:
        #     if outbound.reply_to_verkey

        # always populate connection targets using provided context
        if not outbound.target and not outbound.target_list and outbound.connection_id:
            mgr = ConnectionManager(context)
            try:
                outbound.target_list = await mgr.get_connection_targets(
                    connection_id=outbound.connection_id
                )
            except ConnectionManagerError:
                LOGGER.exception("Error preparing outbound message for transmission")
                return

        targets = [outbound.target] if outbound.target else (outbound.target_list or [])
        transport_id = None
        out_mgr = self.outbound_transport_manager
        for target in targets:
            endpoint = target.endpoint
            transport_id = out_mgr.get_running_transport_for_endpoint(endpoint)
            if transport_id:
                break
        if not transport_id:

            # Add message to outbound queue, indexed by key
            # if self.undelivered_queue:
            #     self.undelivered_queue.add_message(message)

            LOGGER.warning("Cannot queue message for delivery, no supported transport")
            return  # drop message

        queued = QueuedOutboundMessage(context, outbound, target, transport_id)
        self.outbound_new.append(queued)
        self.outbound_event.set()

    async def process_outbound(self):
        """Continually watch the outbound buffer and send to transports."""

        while True:
            # if self.stopping .. break

            self.outbound_event.clear()
            loop_time = time.perf_counter()
            upd_buffer = []

            for queued in self.outbound_buffer:
                if queued.state == QueuedOutboundMessage.STATE_DONE:
                    if queued.error:
                        LOGGER.exception(
                            "Outbound message could not be delivered",
                            exc_info=queued.error,
                        )
                    continue  # remove from buffer

                deliver = False

                if queued.state == QueuedOutboundMessage.STATE_PENDING:
                    deliver = True
                elif queued.state == QueuedOutboundMessage.STATE_RETRY:
                    if queued.retry_at < loop_time:
                        queued.retry_at = None
                        deliver = True

                if deliver:
                    queued.state = QueuedOutboundMessage.STATE_DELIVER
                    await self.deliver_queued_message(queued)

                upd_buffer.append(queued)

            new_messages = self.outbound_new.copy()
            self.outbound_new = []
            for queued in new_messages:

                if queued.message.enc_payload:
                    queued.payload = queued.message.enc_payload
                    queued.state = QueuedOutboundMessage.STATE_DELIVER
                    await self.deliver_queued_message(queued)
                else:
                    queued.state = QueuedOutboundMessage.STATE_ENCODE
                    await self.encode_queued_message(queued)

                upd_buffer.append(queued)

            self.outbound_buffer = upd_buffer
            await self.outbound_event.wait()

    async def encode_queued_message(self, queued: QueuedOutboundMessage):
        transport = self.outbound_transport_manager.get_transport(queued.transport_id)
        wire_format = transport.wire_format or PackWireFormat()
        self.runner.start_task(
            wire_format.encode_message(
                queued.context,
                queued.message.payload,
                queued.target.recipient_keys,
                queued.target.routing_keys,
                queued.target.sender_key,
            ),
            lambda task, exc_info: self.finished_encode(task, queued, exc_info),
        )

    def finished_encode(
        self, task: asyncio.Task, queued: QueuedOutboundMessage, exc_info=None
    ):
        if exc_info:
            queued.error = exc_info
            queued.state = QueuedOutboundMessage.STATE_DONE
        else:
            queued.payload = task.result()
            queued.state = QueuedOutboundMessage.STATE_PENDING
        self.outbound_event.set()

    async def deliver_queued_message(self, queued: QueuedOutboundMessage):
        transport = self.outbound_transport_manager.get_transport(queued.transport_id)
        queued.delivery_task = self.dispatch_runner.start_task(
            transport.handle_message(queued.payload, queued.endpoint),
            lambda task, exc_info: self.finished_deliver(task, queued, exc_info),
        )

    def finished_deliver(
        self, task: asyncio.Task, queued: QueuedOutboundMessage, exc_info=None
    ):
        """Clean up a closed session."""
        if exc_info:
            queued.error = exc_info
            if queued.retries < 5:
                queued.state = QueuedOutboundMessage.STATE_RETRY
                queued.retry_at = time.perf_counter() + 10
            else:
                queued.state = QueuedOutboundMessage.STATE_DONE
        else:
            queued.error = None
            queued.state = QueuedOutboundMessage.STATE_DONE
        queued.delivery_task = None
        self.outbound_event.set()
