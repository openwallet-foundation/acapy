from abc import ABC, abstractmethod

from .responder import BaseResponder
from .request_context import RequestContext


class BaseHandler(ABC):
    @abstractmethod
    def __init__(self) -> None:
        pass

    @abstractmethod
    async def handle(self, context: RequestContext, responder: BaseResponder):
        pass
