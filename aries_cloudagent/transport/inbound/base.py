"""Base inbound transport class."""

from abc import ABC, abstractmethod
from collections import namedtuple
from typing import Awaitable, Callable

from ..base import BaseWireFormat
from ..error import TransportError

from .session import InboundSession


class BaseInboundTransport(ABC):
    """Base inbound transport class."""

    def __init__(
        self, scheme: str, create_session: Callable,
    ):
        self._create_session = create_session
        self._scheme = scheme

    @property
    def scheme(self):
        """Accessor for this transport's scheme."""
        return self._scheme

    def create_session(
        self, client_info: dict = None, wire_format: BaseWireFormat = None,
    ) -> Awaitable[InboundSession]:
        return self._create_session(
            self.scheme, client_info=client_info, wire_format=wire_format
        )

    @abstractmethod
    async def start(self) -> None:
        """Start listening for on this transport."""

    @abstractmethod
    async def stop(self) -> None:
        """Stop listening for on this transport."""


class InboundTransportError(TransportError):
    """Generic inbound transport error."""


class InboundTransportRegistrationError(InboundTransportError):
    """Error in loading an inbound transport."""


class InboundTransportSetupError(InboundTransportError):
    """Setup error for an inbound transport."""


InboundTransportConfiguration = namedtuple(
    "InboundTransportConfiguration", "module host port"
)
