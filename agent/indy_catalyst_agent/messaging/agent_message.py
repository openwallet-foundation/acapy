from abc import ABC, abstractproperty


class AgentMessage(ABC):
    @abstractproperty
    def _type(self) -> str:
        pass
