from typing import Optional
from unittest import IsolatedAsyncioTestCase

from ...config.base import InjectionError
from ...config.injection_context import InjectionContext
from ..error import ProfileSessionInactiveError
from ..profile import Profile, ProfileManagerProvider, ProfileSession


class MockProfile(Profile):
    def session(self, context: Optional[InjectionContext] = None) -> ProfileSession:
        """Start a new interactive session with no transaction support requested."""

    def transaction(self, context: Optional[InjectionContext] = None) -> ProfileSession:
        """
        Start a new interactive session with commit and rollback support.

        If the current backend does not support transactions, then commit
        and rollback operations of the session will not have any effect.
        """


class TestProfileSession(IsolatedAsyncioTestCase):
    async def test_session_active(self):
        profile = MockProfile()
        session = ProfileSession(profile)
        assert not session.is_transaction
        assert session.__class__.__name__ in str(session)

        self.assertFalse(session.active)
        with self.assertRaises(ProfileSessionInactiveError):
            await session.commit()
        with self.assertRaises(ProfileSessionInactiveError):
            await session.rollback()
        with self.assertRaises(ProfileSessionInactiveError):
            session.inject(dict)
        assert profile.inject_or(dict) is None

        await session.__aenter__()

        self.assertTrue(session.active)
        session.context.injector.bind_instance(dict, {})
        assert session.inject_or(dict) is not None
        assert profile.inject_or(dict) is None

        await session.__aexit__(None, None, None)

        self.assertFalse(session.active)

        session2 = ProfileSession(profile)
        self.assertFalse(session2.active)
        assert (await session2) is session2
        self.assertTrue(session2.active)

        await session2.rollback()


class TestProfileManagerProvider(IsolatedAsyncioTestCase):
    async def test_invalid_wallet_type(self):
        context = InjectionContext()
        provider = ProfileManagerProvider()
        context.settings["wallet.type"] = "invalid-type"

        with self.assertRaises(InjectionError):
            provider.provide(context.settings, context.injector)
