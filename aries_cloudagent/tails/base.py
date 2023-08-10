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
        filename: str,
        tails_file_path: str,
        interval: float = 1.0,
        backoff: float = 0.25,
        max_attempts: int = 5,
    ) -> Tuple[bool, str]:
        """Upload tails file to tails server.

        Args:
            context: context with configuration settings
            filename: file name given to tails server
            tails_file: The path to the tails file to upload
            interval: initial interval between attempts
            backoff: exponential backoff in retry interval
            max_attempts: maximum number of attempts to make

        Returns:
            Tuple[bool, str]: tuple with success status and url of uploaded
            file or error message if failed

        """
