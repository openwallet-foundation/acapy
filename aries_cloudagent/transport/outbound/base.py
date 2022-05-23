"""Base outbound transport."""

import asyncio
from abc import ABC, abstractmethod
from typing import Union

from ...core.profile import Profile
from ...utils.stats import Collector

from ..error import TransportError
from ..wire_format import BaseWireFormat


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
        payload: Union[str, bytes],
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
