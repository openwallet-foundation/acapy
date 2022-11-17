"""Abstract admin server interface."""


from abc import ABC, abstractmethod


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
