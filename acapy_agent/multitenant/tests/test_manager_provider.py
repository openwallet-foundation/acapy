from unittest import IsolatedAsyncioTestCase

from ...config.base import InjectionError
from ...config.injection_context import InjectionContext
from ...utils.testing import create_test_profile
from ..manager_provider import MultitenantManagerProvider


class TestProfileManagerProvider(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.profile = await create_test_profile()

    async def test_provide_manager(self):
        provider = MultitenantManagerProvider(self.profile)
        context = InjectionContext()

        self.assertEqual(
            provider.provide(context.settings, context.injector).__class__.__name__,
            "MultitenantManager",
        )

    async def test_provide_askar_profile_manager(self):
        provider = MultitenantManagerProvider(self.profile)
        context = InjectionContext()
        context.settings["multitenant.wallet_type"] = "single-wallet-askar"

        self.assertEqual(
            provider.provide(context.settings, context.injector).__class__.__name__,
            "SingleWalletAskarMultitenantManager",
        )

    async def test_invalid_manager_type(self):
        provider = MultitenantManagerProvider(self.profile)
        context = InjectionContext()
        context.settings["multitenant.wallet_type"] = "not-valid"

        with self.assertRaises(InjectionError):
            provider.provide(context.settings, context.injector)
