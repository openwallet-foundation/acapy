"""Base injection context builder classes."""

from abc import ABC, abstractmethod
from typing import Mapping

from .injection_context import InjectionContext
from .settings import Settings


class ContextBuilder(ABC):
    """Base injection context builder class."""

    def __init__(self, settings: Mapping[str, object] = None):
        """
        Initialize an instance of the context builder.

        Args:
            settings: Mapping of configuration settings

        """
        self.settings = Settings(settings)

    @abstractmethod
    async def build_context(self) -> InjectionContext:
        """Build the base injection context."""

    def update_settings(self, settings: Mapping[str, object]):
        """Update the context builder with additional settings."""
        if settings:
            self.settings = self.settings.extend(settings)
