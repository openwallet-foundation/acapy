"""Base outbound transport."""

from abc import ABC, abstractmethod
import asyncio
from typing import Union

from ...connections.models.connection_target import ConnectionTarget
from ...core.profile import Profile
from ...utils.stats import Collector
from ..error import TransportError
from ..wire_format import BaseWireFormat
from .message import OutboundMessage


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


class BaseOutboundTransport(ABC):
    """Base outbound transport class."""

    def __init__(
        self,
        wire_format: BaseWireFormat = None,
        root_profile: Profile = None,
    ) -> None:
        """Initialize a `BaseOutboundTransport` instance."""
        self._collector = None
        self._wire_format = wire_format
        self.root_profile = root_profile

    @property
    def collector(self) -> Collector:
        """Accessor for the stats collector instance."""
        return self._collector

    @collector.setter
    def collector(self, coll: Collector):
        """Assign a new stats collector instance."""
        self._collector = coll

    @property
    def wire_format(self) -> BaseWireFormat:
        """Accessor for a custom wire format for the transport."""
        return self._wire_format

    @wire_format.setter
    def wire_format(self, format: BaseWireFormat):
        """Setter for a custom wire format for the transport."""
        self._wire_format = format

    async def __aenter__(self):
        """Async context manager enter."""
        await self.start()

    async def __aexit__(self, err_type, err_value, err_t):
        """Async context manager exit."""
        if err_type and err_type != asyncio.CancelledError:
            self.logger.exception("Exception in outbound transport")
        await self.stop()

    @abstractmethod
    async def start(self):
        """Start the transport."""

    @abstractmethod
    async def stop(self):
        """Shut down the transport."""

    @abstractmethod
    async def handle_message(
        self,
        profile: Profile,
        outbound_message: QueuedOutboundMessage,
        endpoint: str,
        metadata: dict = None,
    ):
        """
        Handle message.

        Args:
            profile: the profile that produced the message
            payload: message payload in string or byte format
            endpoint: URI endpoint for delivery
            metadata: Additional metadata associated with the payload
        """


class OutboundTransportError(TransportError):
    """Generic outbound transport error."""


class OutboundTransportRegistrationError(OutboundTransportError):
    """Outbound transport registration error."""


class OutboundDeliveryError(OutboundTransportError):
    """Base exception when a message cannot be delivered via an outbound transport."""
