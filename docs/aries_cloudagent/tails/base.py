"""Tails server interface base class."""

from abc import ABC, abstractmethod, ABCMeta
from typing import Tuple

from ..config.injection_context import InjectionContext


class BaseTailsServer(ABC, metaclass=ABCMeta):
    """Base class for tails server interface."""

    @abstractmethod
    async def upload_tails_file(
        self,
        context: InjectionContext,
        rev_reg_id: str,
        tails_file_path: str,
        interval: float = 1.0,
        backoff: float = 0.25,
        max_attempts: int = 5,
    ) -> Tuple[bool, str]:
        """Upload tails file to tails server.

        Args:
            rev_reg_id: The revocation registry identifier
            tails_file: The path to the tails file to upload
            interval: initial interval between attempts
            backoff: exponential backoff in retry interval
            max_attempts: maximum number of attempts to make
        """
