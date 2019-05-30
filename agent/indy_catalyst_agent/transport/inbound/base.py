"""Base inbound transport class."""

from abc import ABC, abstractmethod

from ...error import BaseError


class BaseInboundTransport(ABC):
    """Base inbound transport class."""

    @abstractmethod
    def start(self) -> None:
        """Start listening for on this transport."""


class TransportSetupError(BaseError):
    """Setup error for an inbound transport."""
