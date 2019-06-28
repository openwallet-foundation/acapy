"""Base inbound transport class."""

from abc import ABC, abstractmethod
from collections import namedtuple

from ...error import BaseError


class BaseInboundTransport(ABC):
    """Base inbound transport class."""

    @abstractmethod
    async def start(self) -> None:
        """Start listening for on this transport."""

    @abstractmethod
    async def stop(self) -> None:
        """Stop listening for on this transport."""


class InboundTransportRegistrationError(BaseError):
    """Error in loading an inbound transport."""


class InboundTransportSetupError(BaseError):
    """Setup error for an inbound transport."""


InboundTransportConfiguration = namedtuple(
    "InboundTransportConfiguration", "module host port"
)
