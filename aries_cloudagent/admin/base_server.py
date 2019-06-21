"""Abstract admin server interface."""


from abc import ABC, abstractmethod
from typing import Sequence


class BaseAdminServer(ABC):
    """Admin HTTP server class."""

    @abstractmethod
    async def start(self) -> None:
        """
        Start the webserver.

        Raises:
            AdminSetupError: If there was an error starting the webserver

        """

    @abstractmethod
    async def stop(self) -> None:
        """Stop the webserver."""

    @abstractmethod
    def add_webhook_target(
        self, target_url: str, topic_filter: Sequence[str] = None, retries: int = None
    ):
        """Add a webhook target."""

    @abstractmethod
    def remove_webhook_target(self, target_url: str):
        """Remove a webhook target."""

    @abstractmethod
    async def send_webhook(self, topic: str, payload: dict):
        """Add a webhook to the queue, to send to all registered targets."""
