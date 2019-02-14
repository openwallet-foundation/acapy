from abc import ABC, abstractmethod


class BaseOutboundMessageQueue(ABC):
    """ """
    @abstractmethod
    async def enqueue(self, message):
        pass

    @abstractmethod
    async def dequeue(self):
        pass

    @abstractmethod
    def __aiter__(self):
        pass

    @abstractmethod
    async def __anext__(self):
        pass
