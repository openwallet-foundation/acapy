from asynctest import TestCase as AsyncTestCase

from ...config.injection_context import InjectionContext
from ...config.base import InjectionError
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

    async def test_provide_askar_profile_manager(self):
        profile = InMemoryProfile.test_profile()
        provider = MultitenantManagerProvider(profile)
        context = InjectionContext()
        context.settings["multitenant.wallet_type"] = "askar-profile"

        self.assertEqual(
            provider.provide(context.settings, context.injector).__class__.__name__,
            "AskarProfileMultitenantManager",
        )

    async def test_invalid_manager_type(self):
        profile = InMemoryProfile.test_profile()
        provider = MultitenantManagerProvider(profile)
        context = InjectionContext()
        context.settings["multitenant.wallet_type"] = "not-valid"

        with self.assertRaises(InjectionError):
            provider.provide(context.settings, context.injector)
