from abc import ABC, abstractproperty, abstractclassmethod, abstractmethod


class AgentMessage(ABC):
    @abstractproperty
    def _type(self) -> str:
        pass

    @abstractmethod
    def serialize(self) -> dict:
        pass

    @abstractclassmethod
    def deserialize(cls):
        pass
