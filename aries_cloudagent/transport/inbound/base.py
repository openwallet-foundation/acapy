"""Base inbound transport class."""

from abc import ABC, abstractmethod
from collections import namedtuple
from typing import Awaitable, Callable

from ..error import TransportError
from ..wire_format import BaseWireFormat

from .session import InboundSession


class BaseInboundTransport(ABC):
    """Base inbound transport class."""

    def __init__(
        self, scheme: str, create_session: Callable,
    ):
        """Initialize the inbound transport instance."""
        self._create_session = create_session
        self._scheme = scheme
        self.wire_format: BaseWireFormat = None

    @property
    def scheme(self):
        """Accessor for this transport's scheme."""
        return self._scheme

    def create_session(
        self,
        *,
        accept_undelivered: bool = False,
        can_respond: bool = False,
        client_info: dict = None,
        wire_format: BaseWireFormat = None,
    ) -> Awaitable[InboundSession]:
        """
        Create a new inbound session.

        Args:
            accept_undelivered: Flag for accepting undelivered messages
            can_respond: Flag indicating that the transport can send responses
            client_info: Request-specific client information
            wire_format: Optionally override the session wire format
        """
        return self._create_session(
            accept_undelivered=accept_undelivered,
            can_respond=can_respond,
            client_info=client_info,
            wire_format=wire_format or self.wire_format,
            transport_type=self.scheme,
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
