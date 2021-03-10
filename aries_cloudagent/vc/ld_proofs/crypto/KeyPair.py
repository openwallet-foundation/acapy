from abc import ABC, abstractmethod


class KeyPair(ABC):
    @abstractmethod
    async def sign(self, message: bytes) -> bytes:
        pass

    @abstractmethod
    async def verify(self, message: bytes) -> bool:
        pass
