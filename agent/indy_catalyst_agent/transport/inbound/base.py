"""Base inbound transport class."""

from abc import ABC, abstractmethod


class BaseInboundTransport(ABC):
    """Base inbound transport class."""

    @abstractmethod
    def start(self) -> None:
        """Start listening for on this transport."""
