from asynctest import TestCase

from ..base import BaseService
from ..factory import ServiceFactory, ServiceRegistry
from ...messaging.base_context import BaseRequestContext


class ContextImpl(BaseRequestContext):
    pass


class ServiceImpl(BaseService):
    def __init__(self, ctx: BaseRequestContext):
        self._context = ctx

    @staticmethod
    async def get_instance(ctx: BaseRequestContext):
        return ServiceImpl(ctx)


class TestServiceFactory(TestCase):
    test_service_name = "SERVICE"
    test_not_service_name = "NOT_SERVICE"

    def setUp(self):
        self.context = ContextImpl()

    async def test_registration(self):
        registry = ServiceRegistry()
        registry.register_service_handler(
            self.test_service_name, ServiceImpl.get_instance
        )
        factory = registry.get_factory(self.context)
        instance = await factory.resolve_service(self.test_service_name)
        assert isinstance(instance, ServiceImpl)
        assert instance._context is self.context
        instance = await factory.resolve_service(self.test_not_service_name)
        assert instance is None

    async def test_failure(self):
        registry = ServiceRegistry()
        factory = registry.get_factory(self.context)
        instance = await factory.resolve_service(self.test_service_name)
        assert instance is None
