import logging

from abc import ABC, abstractmethod, abstractproperty
from typing import Callable, Dict, Iterable

from .message import OutboundMessage
from .queue.base import BaseOutboundMessageQueue


class BaseOutboundTransport(ABC):
    @abstractmethod
    def __init__(self, queue: BaseOutboundMessageQueue) -> None:
        pass

    @abstractmethod
    async def __aenter__(self):
        pass

    @abstractmethod
    async def __aexit__(self, *err):
        pass

    @abstractproperty
    def queue(self):
        pass

    @abstractmethod
    async def handle_message(self, message: OutboundMessage):
        pass

    async def start(self) -> None:
        async for message in self.queue:
            await self.handle_message(message)
