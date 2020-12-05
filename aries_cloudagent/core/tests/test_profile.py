import asyncio

from asynctest import TestCase as AsyncTestCase, mock as async_mock

from ...config.base import ProviderError
from ...config.injection_context import InjectionContext

from ..error import ProfileSessionInactiveError
from ..profile import ProfileManagerProvider, ProfileSession


class TestProfileSession(AsyncTestCase):
    async def test_session_active(self):
        profile = async_mock.MagicMock()
        session = ProfileSession(profile)

        self.assertEqual(session.active, False)
        with self.assertRaises(ProfileSessionInactiveError):
            await session.commit()
        with self.assertRaises(ProfileSessionInactiveError):
            await session.rollback()
        with self.assertRaises(ProfileSessionInactiveError):
            session.inject(dict)

        await session.__aenter__()

        self.assertEqual(session.active, True)

        await session.__aexit__(None, None, None)

        self.assertEqual(session.active, False)

        session2 = ProfileSession(profile)
        self.assertEqual(session2.active, False)
        assert (await session2) is session2
        self.assertEqual(session2.active, True)


class TestProfileManagerProvider(AsyncTestCase):
    async def test_basic_wallet_type(self):
        context = InjectionContext()
        provider = ProfileManagerProvider(context)
        context.settings["wallet.type"] = "basic"

        self.assertEqual(
            provider.provide(context.settings, context.injector).__class__.__name__,
            "InMemoryProfileManager",
        )

        context.settings["wallet.type"] = "in_memory"

        self.assertEqual(
            provider.provide(context.settings, context.injector).__class__.__name__,
            "InMemoryProfileManager",
        )

    async def test_invalid_wallet_type(self):
        context = InjectionContext()
        provider = ProfileManagerProvider(context)
        context.settings["wallet.type"] = "invalid-type"

        with self.assertRaises(ProviderError):
            provider.provide(context.settings, context.injector)
