"""Base inbound transport class."""

from abc import ABC, abstractmethod
from collections import namedtuple
from typing import Awaitable, Callable

from ...core.profile import Profile
from ..error import TransportError
from ..wire_format import BaseWireFormat
from .session import InboundSession


class BaseInboundTransport(ABC):
    """Base inbound transport class."""

    def __init__(
        self,
        scheme: str,
        create_session: Callable,
        *,
        max_message_size: int = 0,
        is_external: bool = False,
        wire_format: BaseWireFormat = None,
        root_profile: Profile = None,
    ):
        """
        Initialize the inbound transport instance.

        Args:
            scheme: The transport scheme identifier
            create_session: Method to create a new inbound session
        """

        self._create_session = create_session
        self._max_message_size = max_message_size
        self._scheme = scheme
        self.wire_format: BaseWireFormat = wire_format
        self.root_profile: Profile = root_profile
        self._is_external = is_external

    @property
    def max_message_size(self):
        """Accessor for this transport's max message size."""
        return self._max_message_size

    @property
    def scheme(self):
        """Accessor for this transport's scheme."""
        return self._scheme

    @property
    def is_external(self):
        """Accessor for this transport's is_external."""
        return self._is_external

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
