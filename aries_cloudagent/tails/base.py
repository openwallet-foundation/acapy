"""Tails server interface base class."""

from abc import ABC, abstractmethod, ABCMeta

from ..config.injection_context import InjectionContext


class BaseTailsServer(ABC, metaclass=ABCMeta):
    """Base class for tails server interface."""

    @abstractmethod
    async def upload_tails_file(
        self, context: InjectionContext, rev_reg_id: str, tails_file_path: str
    ) -> (bool, str):
        """Upload tails file to tails server.

        Args:
            rev_reg_id: The revocation registry identifier
            tails_file: The path to the tails file to upload
        """
