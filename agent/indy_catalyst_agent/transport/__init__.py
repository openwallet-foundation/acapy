from abc import ABC, abstractmethod
from typing import Callable


class InvalidTransportError(Exception):
    pass


class Transport(ABC):
    @abstractmethod
    def setup(self, message_router: Callable) -> None:
        raise NotImplementedError() # pragma: no cover
