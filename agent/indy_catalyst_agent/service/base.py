"""Service management base classes."""

from abc import ABC, abstractmethod


class BaseService(ABC):
    """Abstract base service class."""


class BaseServiceFactory(ABC):
    """Abstract base service factory class."""

    @abstractmethod
    async def resolve_service(self, service_name: str) -> BaseService:
        """
        Resolve a service name to an instance of the service.

        Args:
            service_name: Service name to resolve
            context: The request context to use in the service lookup and initialization

        Returns:
            A service instance or None if there is no service by that name.

        """
