from abc import ABC, abstractmethod
from typing import Callable


class BaseInboundTransport(ABC):
    """ """
    @abstractmethod
    def start(self, message_router: Callable) -> None:
        """

        :param message_router: Callable: 

        """
        pass
