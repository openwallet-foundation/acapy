from abc import ABC, abstractmethod
from typing import Callable


class InvalidTransportError(Exception):
    pass


class BaseTransport(ABC):
    @abstractmethod
    def start(self, message_router: Callable) -> None:
        pass
