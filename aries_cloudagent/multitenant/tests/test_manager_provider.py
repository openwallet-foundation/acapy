from asynctest import TestCase as AsyncTestCase

from ...config.injection_context import InjectionContext
from ..manager_provider import MultitenantManagerProvider
from ...core.in_memory import InMemoryProfile

class TestProfileManagerProvider(AsyncTestCase):
    async def test_provide_manager(self):
        profile = InMemoryProfile.test_profile()
        provider = MultitenantManagerProvider(profile)
        context = InjectionContext()

        self.assertEqual(
            provider.provide(context.settings, context.injector).__class__.__name__,
            "MultitenantManager",
        )

        context.settings["multitenant.type"] = "askar"

        self.assertEqual(
            provider.provide(context.settings, context.injector).__class__.__name__,
            "AskarProfileMultitenantManager",
        )
