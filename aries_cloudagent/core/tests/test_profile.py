from asynctest import TestCase as AsyncTestCase

from ...config.base import InjectionError
from ...config.injection_context import InjectionContext

from ..error import ProfileSessionInactiveError
from ..profile import Profile, ProfileManagerProvider, ProfileSession


class MockProfile(Profile):
    def session(self, context: InjectionContext = None) -> ProfileSession:
        """Start a new interactive session with no transaction support requested."""

    def transaction(self, context: InjectionContext = None) -> ProfileSession:
        """
        Start a new interactive session with commit and rollback support.

        If the current backend does not support transactions, then commit
        and rollback operations of the session will not have any effect.
        """


class TestProfileSession(AsyncTestCase):
    async def test_session_active(self):
        profile = MockProfile()
        session = ProfileSession(profile)
        assert not session.is_transaction
        assert session.__class__.__name__ in str(session)

        self.assertEqual(session.active, False)
        with self.assertRaises(ProfileSessionInactiveError):
            await session.commit()
        with self.assertRaises(ProfileSessionInactiveError):
            await session.rollback()
        with self.assertRaises(ProfileSessionInactiveError):
            session.inject(dict)
        assert profile.inject_or(dict) is None

        await session.__aenter__()

        self.assertEqual(session.active, True)
        session.context.injector.bind_instance(dict, dict())
        assert session.inject_or(dict) is not None
        assert profile.inject_or(dict) is None

        await session.__aexit__(None, None, None)

        self.assertEqual(session.active, False)

        session2 = ProfileSession(profile)
        self.assertEqual(session2.active, False)
        assert (await session2) is session2
        self.assertEqual(session2.active, True)

        await session2.rollback()


class TestProfileManagerProvider(AsyncTestCase):
    async def test_basic_wallet_type(self):
        context = InjectionContext()
        provider = ProfileManagerProvider()
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
        provider = ProfileManagerProvider()
        context.settings["wallet.type"] = "invalid-type"

        with self.assertRaises(InjectionError):
            provider.provide(context.settings, context.injector)
