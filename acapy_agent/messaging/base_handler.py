"""A Base handler class for all message handlers."""

import logging
from abc import ABC, abstractmethod

from ..core.error import BaseError
from .request_context import RequestContext
from .responder import BaseResponder


class HandlerException(BaseError):
    """Exception base class for generic handler errors."""


class BaseHandler(ABC):
    """Abstract base class for handlers."""

    def __init__(self) -> None:
        """Initialize a BaseHandler instance."""
        self._logger = logging.getLogger(__name__)

    @abstractmethod
    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Abstract method for handler logic.

        Args:
            context: Request context object
            responder: A responder object

        """
