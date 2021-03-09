from abc import ABC, abstractmethod


class KeyPair(ABC):
    @abstractmethod
    def sign(self, message):
        pass

    @abstractmethod
    def verify(self, message):
        pass
