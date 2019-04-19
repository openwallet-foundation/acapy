"""Handle service registration and retrieval of service instances."""

from typing import Awaitable, Callable, Generic, TypeVar

from .base import BaseService, BaseServiceFactory
from ..messaging.base_context import BaseRequestContext

T = TypeVar("T", bound=BaseRequestContext)


class ServiceRegistry(Generic[T]):
    """Service registry for assembling services."""

    def __init__(self):
        """Initialize a ServiceRegistry instance."""
        self._svcmap = {}

    def register_service_handler(
        self, service_name: str, ctor: Callable[[T], Awaitable[BaseService]]
    ):
        """
        Add new registered service.

        Args:
            service_name: The unique name of the service
            ctor: Constructor coroutine which returns an instance of the service given
                a `RequestContext`

        """
        self._svcmap[service_name] = ctor

    def unregister_service(self, service_name: str):
        """Unregister a service.

        Args:
            service_name: The unique identifier of the service
        """
        if service_name in self._svcmap:
            del self._svcmap[service_name]

    def resolve_service_handler(
        self, service_name: str
    ) -> Callable[[T], Awaitable[BaseService]]:
        """Resolve a registered service by name."""
        return self._svcmap.get(service_name)

    def get_factory(self, context: T):
        """Create a new service factory for this registry."""
        return ServiceFactory(context, self)

    def __repr__(self) -> str:
        """Return a string representation for this class."""
        return "<{}>".format(self.__class__.__name__)


class ServiceFactory(BaseServiceFactory, Generic[T]):
    """Service factory for getting an instance of a registered service."""

    def __init__(self, context: T, registry: ServiceRegistry[T]):
        """Initialize a ServiceFactory instance."""
        self._context = context
        self._registry = registry

    async def resolve_service(self, service_name: str) -> BaseService:
        """
        Resolve a service name to an instance of the service.

        Args:
            service_name: Service name to resolve
            context: The request context to use in the service lookup and initialization

        Returns:
            A service instance or None if there is no service by that name.

        """
        ctor = self._registry.resolve_service_handler(service_name)
        instance = await ctor(self._context) if ctor else None
        return instance

    def __repr__(self) -> str:
        """Return a string representation for this class."""
        return "<{}>".format(self.__class__.__name__)
