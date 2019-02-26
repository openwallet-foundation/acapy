"""Base inbound transport class."""

from abc import ABC, abstractmethod
from typing import Callable


class BaseInboundTransport(ABC):
    """Base inbound transport class."""

    @abstractmethod
    def start(self, message_router: Callable) -> None:
        """
        Start listening for on this transport.

        Args:
            message_router: Function to call to route messages

        """
        pass
