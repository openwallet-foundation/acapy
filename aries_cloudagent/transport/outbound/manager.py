"""Outbound transport manager."""

import asyncio
import json
import logging
import time

from typing import Callable, Type, Union
from urllib.parse import urlparse

from ...connections.models.connection_target import ConnectionTarget
from ...core.profile import Profile
from ...utils.classloader import ClassLoader, ModuleLoadError, ClassNotFoundError
from ...utils.stats import Collector
from ...utils.task_queue import CompletedTask, TaskQueue, task_exc_info

from ...utils.tracing import trace_event, get_timer

from ..wire_format import BaseWireFormat

from .base import (
    BaseOutboundTransport,
    OutboundDeliveryError,
    OutboundTransportRegistrationError,
)
from .message import OutboundMessage

LOGGER = logging.getLogger(__name__)
MODULE_BASE_PATH = "aries_cloudagent.transport.outbound"


class QueuedOutboundMessage:
    """Class representing an outbound message pending delivery."""

    STATE_NEW = "new"
    STATE_PENDING = "pending"
    STATE_ENCODE = "encode"
    STATE_DELIVER = "deliver"
    STATE_RETRY = "retry"
    STATE_DONE = "done"

    def __init__(
        self,
        profile: Profile,
        message: OutboundMessage,
        target: ConnectionTarget,
        transport_id: str,
    ):
        """Initialize the queued outbound message."""
        self.profile = profile
        self.endpoint = target and target.endpoint
        self.error: Exception = None
        self.message = message
        self.payload: Union[str, bytes] = None
        self.retries = None
        self.retry_at: float = None
        self.state = self.STATE_NEW
        self.target = target
        self.task: asyncio.Task = None
        self.transport_id: str = transport_id
        self.metadata: dict = None
        self.api_key: str = None


class OutboundTransportManager:
    """Outbound transport manager class."""

    MAX_RETRY_COUNT = 4

    def __init__(self, profile: Profile, handle_not_delivered: Callable = None):
        """
        Initialize a `OutboundTransportManager` instance.

        Args:
            root_profile: The application root profile
            handle_not_delivered: An optional handler for undelivered messages

        """
        self.root_profile = profile
        self.loop = asyncio.get_event_loop()
        self.handle_not_delivered = handle_not_delivered
        self.outbound_buffer = []
        self.outbound_event = asyncio.Event()
        self.outbound_new = []
        self.registered_schemes = {}
        self.registered_transports = {}
        self.running_transports = {}
        self.task_queue = TaskQueue(max_active=200)
        self._process_task: asyncio.Task = None
        if self.root_profile.settings.get("transport.max_outbound_retry"):
            self.MAX_RETRY_COUNT = self.root_profile.settings[
                "transport.max_outbound_retry"
            ]

    async def setup(self):
        """Perform setup operations."""
        outbound_transports = (
            self.root_profile.settings.get("transport.outbound_configs") or []
        )
        for outbound_transport in outbound_transports:
            self.register(outbound_transport)

    def register(self, module_name: str) -> str:
        """
        Register a new outbound transport by module path.

        Args:
            module_name: Module name to register

        Raises:
            OutboundTransportRegistrationError: If the imported class cannot
                be located
            OutboundTransportRegistrationError: If the imported class does not
                specify a schemes attribute
            OutboundTransportRegistrationError: If the scheme has already been
                registered

        """
        try:
            if "." in module_name:
                package, module = module_name.split(".", 1)
            else:
                package = MODULE_BASE_PATH
                module = module_name

            imported_class = ClassLoader.load_subclass_of(
                BaseOutboundTransport, module, package
            )
        except (ModuleLoadError, ClassNotFoundError) as e:
            raise OutboundTransportRegistrationError(
                f"Outbound transport module {module} could not be resolved."
            ) from e

        return self.register_class(imported_class)

    def register_class(
        self, transport_class: Type[BaseOutboundTransport], transport_id: str = None
    ) -> str:
        """
        Register a new outbound transport class.

        Args:
            transport_class: Transport class to register

        Raises:
            OutboundTransportRegistrationError: If the imported class does not
                specify a schemes attribute
            OutboundTransportRegistrationError: If the scheme has already been
                registered

        """
        try:
            schemes = transport_class.schemes
        except AttributeError:
            raise OutboundTransportRegistrationError(
                f"Imported class {transport_class} does not "
                + "specify a required 'schemes' attribute"
            )
        if not transport_id:
            transport_id = transport_class.__qualname__

        for scheme in schemes:
            if scheme in self.registered_schemes:
                # A scheme can only be registered once
                raise OutboundTransportRegistrationError(
                    f"Cannot register transport '{transport_id}'"
                    f"for '{scheme}' scheme because the scheme"
                    "has already been registered"
                )

        self.registered_transports[transport_id] = transport_class

        for scheme in schemes:
            self.registered_schemes[scheme] = transport_id

        return transport_id

    async def start_transport(self, transport_id: str):
        """Start a registered transport."""
        transport = self.registered_transports[transport_id](
            root_profile=self.root_profile
        )
        transport.collector = self.root_profile.inject_or(Collector)
        await transport.start()
        self.running_transports[transport_id] = transport

    async def start(self):
        """Start all transports and feed messages from the queue."""
        for transport_id in self.registered_transports:
            self.task_queue.run(self.start_transport(transport_id))

    async def stop(self, wait: bool = True):
        """Stop all running transports."""
        if self._process_task and not self._process_task.done():
            self._process_task.cancel()
        await self.task_queue.complete(None if wait else 0)
        for transport in self.running_transports.values():
            await transport.stop()
        self.running_transports = {}

    def get_registered_transport_for_scheme(self, scheme: str) -> str:
        """Find the registered transport ID for a given scheme."""
        try:
            return next(
                transport_id
                for transport_id, transport in self.registered_transports.items()
                if scheme in transport.schemes
            )
        except StopIteration:
            pass

    def get_running_transport_for_scheme(self, scheme: str) -> str:
        """Find the running transport ID for a given scheme."""
        try:
            return next(
                transport_id
                for transport_id, transport in self.running_transports.items()
                if scheme in transport.schemes
            )
        except StopIteration:
            pass

    def get_external_running_transport(self) -> str:
        """Find the external running transport ID."""
        try:
            return next(
                transport_id
                for transport_id, transport in self.running_transports.items()
                if transport.is_external
            )
        except StopIteration:
            pass

    def get_running_transport_for_endpoint(self, endpoint: str):
        """Find the running transport ID to use for a given endpoint."""
        # Grab the scheme from the uri
        scheme = urlparse(endpoint).scheme
        if scheme == "":
            raise OutboundDeliveryError(
                f"The uri '{endpoint}' does not specify a scheme"
            )

        # Look up transport that is registered to handle this scheme
        transport_id = self.get_running_transport_for_scheme(scheme)
        if not transport_id:
            raise OutboundDeliveryError(
                f"No transport driver exists to handle scheme '{scheme}'"
            )
        return transport_id

    def get_transport_instance(self, transport_id: str) -> BaseOutboundTransport:
        """Get an instance of a running transport by ID."""
        return self.running_transports[transport_id]

    async def enqueue_message(self, profile: Profile, outbound: OutboundMessage):
        """
        Add an outbound message to the queue.

        Args:
            profile: The active profile for the request
            outbound: The outbound message to deliver
        """
        targets = [outbound.target] if outbound.target else (outbound.target_list or [])
        transport_id = None
        for target in targets:
            endpoint = target.endpoint
            try:
                transport_id = self.get_external_running_transport()
                if not transport_id:
                    transport_id = self.get_running_transport_for_endpoint(endpoint)
            except OutboundDeliveryError:
                pass
            if transport_id:
                break
        if not transport_id:
            raise OutboundDeliveryError("No supported transport for outbound message")
        transport = self.get_transport_instance(transport_id)
        if transport.is_external:
            encoded_outbound_message = await self.encode_outbound_message(
                profile, outbound, target
            )
            await transport.handle_message(
                profile, encoded_outbound_message.payload, target.endpoint
            )
        else:
            queued = QueuedOutboundMessage(profile, outbound, target, transport_id)
            queued.retries = self.MAX_RETRY_COUNT
            self.outbound_new.append(queued)
            self.process_queued()

    async def encode_outbound_message(
        self, profile: Profile, outbound: OutboundMessage, target: ConnectionTarget
    ):
        """
        Encode outbound message for the target.

        Args:
            profile: The active profile for the request
            outbound: The outbound message to deliver
            target: The outbound message target
        """

        outbound_message = QueuedOutboundMessage(profile, outbound, target, None)

        if outbound_message.message.enc_payload:
            outbound_message.payload = outbound_message.message.enc_payload
        else:
            await self.perform_encode(outbound_message)

        return outbound_message

    def enqueue_webhook(
        self,
        topic: str,
        payload: dict,
        endpoint: str,
        max_attempts: int = None,
        metadata: dict = None,
    ):
        """
        Add a webhook to the queue.

        Args:
            topic: The webhook topic
            payload: The webhook payload
            endpoint: The webhook endpoint
            max_attempts: Override the maximum number of attempts
            metadata: Additional metadata associated with the payload

        Raises:
            OutboundDeliveryError: if the associated transport is not running

        """
        transport_id = self.get_running_transport_for_endpoint(endpoint)
        queued = QueuedOutboundMessage(None, None, None, transport_id)
        if len(endpoint.split("#")) > 1:
            endpoint_hash_split = endpoint.split("#")
            endpoint = endpoint_hash_split[0]
            api_key = endpoint_hash_split[1]
            queued.api_key = api_key
        queued.endpoint = f"{endpoint}/topic/{topic}/"
        queued.metadata = metadata
        queued.payload = json.dumps(payload)
        queued.state = QueuedOutboundMessage.STATE_PENDING
        queued.retries = 4 if max_attempts is None else max_attempts - 1
        self.outbound_new.append(queued)
        self.process_queued()

    def process_queued(self) -> asyncio.Task:
        """
        Start the process to deliver queued messages if necessary.

        Returns: the current queue processing task or None

        """
        if self._process_task and not self._process_task.done():
            self.outbound_event.set()
        elif self.outbound_new or self.outbound_buffer:
            self._process_task = self.loop.create_task(self._process_loop())
            self._process_task.add_done_callback(lambda task: self._process_done(task))
        return self._process_task

    def _process_done(self, task: asyncio.Task):
        """Handle completion of the drain process."""
        exc_info = task_exc_info(task)
        if exc_info:
            LOGGER.exception(
                "Exception in outbound queue processing:", exc_info=exc_info
            )
        if self._process_task and self._process_task.done():
            self._process_task = None

    async def _process_loop(self):
        """Continually kick off encoding and delivery on outbound messages."""
        # Note: this method should not call async methods apart from
        # waiting for the updated event, to avoid yielding to other queue methods

        while True:
            self.outbound_event.clear()
            loop_time = get_timer()
            upd_buffer = []
            retry_count = 0

            for queued in self.outbound_buffer:
                if queued.state == QueuedOutboundMessage.STATE_DONE:
                    if queued.error:
                        LOGGER.exception(
                            "Outbound message could not be delivered to %s",
                            queued.endpoint,
                            exc_info=queued.error,
                        )
                        if self.handle_not_delivered and queued.message:
                            self.handle_not_delivered(queued.profile, queued.message)
                    continue  # remove from buffer

                deliver = False

                if queued.state == QueuedOutboundMessage.STATE_PENDING:
                    deliver = True
                elif queued.state == QueuedOutboundMessage.STATE_RETRY:
                    if queued.retry_at < loop_time:
                        queued.retry_at = None
                        deliver = True
                    else:
                        retry_count += 1

                if deliver:
                    queued.state = QueuedOutboundMessage.STATE_DELIVER
                    p_time = trace_event(
                        self.root_profile.settings,
                        queued.message if queued.message else queued.payload,
                        outcome="OutboundTransportManager.DELIVER.START."
                        + queued.endpoint,
                    )
                    self.deliver_queued_message(queued)
                    trace_event(
                        self.root_profile.settings,
                        queued.message if queued.message else queued.payload,
                        outcome="OutboundTransportManager.DELIVER.END."
                        + queued.endpoint,
                        perf_counter=p_time,
                    )

                upd_buffer.append(queued)

            new_pending = 0
            new_messages = self.outbound_new
            self.outbound_new = []

            for queued in new_messages:
                if queued.state == QueuedOutboundMessage.STATE_NEW:
                    if queued.message and queued.message.enc_payload:
                        queued.payload = queued.message.enc_payload
                        queued.state = QueuedOutboundMessage.STATE_PENDING
                        new_pending += 1
                    else:
                        queued.state = QueuedOutboundMessage.STATE_ENCODE
                        p_time = trace_event(
                            self.root_profile.settings,
                            queued.message if queued.message else queued.payload,
                            outcome="OutboundTransportManager.ENCODE.START",
                        )
                        self.encode_queued_message(queued)
                        trace_event(
                            self.root_profile.settings,
                            queued.message if queued.message else queued.payload,
                            outcome="OutboundTransportManager.ENCODE.END",
                            perf_counter=p_time,
                        )
                else:
                    new_pending += 1

                upd_buffer.append(queued)

            self.outbound_buffer = upd_buffer
            if self.outbound_buffer:
                if (not new_pending) and (not retry_count):
                    await self.outbound_event.wait()
                elif retry_count:
                    # only retries - yield here so we don't hog resources
                    await asyncio.sleep(0.05)
            else:
                break

    def encode_queued_message(self, queued: QueuedOutboundMessage) -> asyncio.Task:
        """Kick off encoding of a queued message."""

        transport = self.get_transport_instance(queued.transport_id)

        queued.task = self.task_queue.run(
            self.perform_encode(queued, transport.wire_format),
            lambda completed: self.finished_encode(queued, completed),
        )
        return queued.task

    async def perform_encode(
        self, queued: QueuedOutboundMessage, wire_format: BaseWireFormat = None
    ):
        """Perform message encoding."""
        wire_format = wire_format or self.root_profile.inject(BaseWireFormat)

        session = await queued.profile.session()
        queued.payload = await wire_format.encode_message(
            session,
            queued.message.payload,
            queued.target.recipient_keys,
            queued.target.routing_keys,
            queued.target.sender_key,
        )

    def finished_encode(self, queued: QueuedOutboundMessage, completed: CompletedTask):
        """Handle completion of queued message encoding."""
        if completed.exc_info:
            queued.error = completed.exc_info
            queued.state = QueuedOutboundMessage.STATE_DONE
        else:
            queued.state = QueuedOutboundMessage.STATE_PENDING
        queued.task = None
        self.process_queued()

    def deliver_queued_message(self, queued: QueuedOutboundMessage) -> asyncio.Task:
        """Kick off delivery of a queued message."""
        transport = self.get_transport_instance(queued.transport_id)
        queued.task = self.task_queue.run(
            transport.handle_message(
                queued.profile,
                queued.payload,
                queued.endpoint,
                queued.metadata,
                queued.api_key,
            ),
            lambda completed: self.finished_deliver(queued, completed),
        )
        return queued.task

    def finished_deliver(self, queued: QueuedOutboundMessage, completed: CompletedTask):
        """Handle completion of queued message delivery."""
        if completed.exc_info:
            queued.error = completed.exc_info

            if queued.retries:
                if LOGGER.isEnabledFor(logging.DEBUG):
                    LOGGER.error(
                        (
                            ">>> Error when posting to: %s; "
                            "Error: %s; "
                            "Payload: %s; Re-queue failed message ..."
                        ),
                        queued.endpoint,
                        queued.error,
                        queued.payload,
                    )
                else:
                    LOGGER.error(
                        (
                            ">>> Error when posting to: %s; "
                            "Error: %s; Re-queue failed message ..."
                        ),
                        queued.endpoint,
                        queued.error,
                    )
                queued.retries -= 1
                queued.state = QueuedOutboundMessage.STATE_RETRY
                queued.retry_at = time.perf_counter() + 10
            else:
                LOGGER.exception(
                    ">>> Outbound message failed to deliver, NOT Re-queued.",
                    exc_info=queued.error,
                )
                queued.state = QueuedOutboundMessage.STATE_DONE
        else:
            queued.error = None
            queued.state = QueuedOutboundMessage.STATE_DONE
        queued.task = None
        self.process_queued()

    async def flush(self):
        """Wait for any queued messages to be delivered."""
        proc_task = self.process_queued()
        if proc_task:
            await proc_task
