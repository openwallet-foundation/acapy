"""Manage in-memory profile interaction."""

from collections import OrderedDict

from ..config.injection_context import InjectionContext
from ..core.profile import Profile, ProfileSession
from ..storage.base import BaseStorage
from ..utils.classloader import ClassLoader
from ..wallet.base import BaseWallet

STORAGE_CLASS = None
WALLET_CLASS = None


class InMemoryProfile(Profile):
    """
    Provide access to in-memory profile management.

    Used primarily for testing.
    """

    BACKEND_NAME = "in_memory"
    TEST_NAME = "test-profile"

    def __init__(self, *, context: InjectionContext = None, name: str = None):
        """Create a new InMemoryProfile instance."""
        global STORAGE_CLASS, WALLET_CLASS
        super().__init__(context=context, name=name)
        self.keys = {}
        self.local_dids = {}
        self.pair_dids = {}
        self.records = OrderedDict()

        if not STORAGE_CLASS:
            STORAGE_CLASS = ClassLoader.load_class(
                "aries_cloudagent.storage.in_memory.InMemoryStorage"
            )
            WALLET_CLASS = ClassLoader.load_class(
                "aries_cloudagent.wallet.in_memory.InMemoryWallet"
            )

    async def start_session(self) -> "ProfileSession":
        """Start a new interactive session with no transaction support requested."""
        context = self.context.start_scope("session")
        return InMemoryProfileSession(self, context)

    async def start_transaction(self) -> "ProfileSession":
        """
        Start a new interactive session with commit and rollback support.

        If the current backend does not support transactions, then commit
        and rollback operations of the session will not have any effect.
        """
        return InMemoryProfileSession(self)

    @classmethod
    def test_instance(cls) -> "InMemoryProfile":
        """Used in tests to create a standard InMemoryProfile."""
        return InMemoryProfile(name=InMemoryProfile.TEST_NAME)

    @classmethod
    def test_session(cls) -> "InMemoryProfileSession":
        """Used in tests to quickly create InMemoryProfileSession."""
        return InMemoryProfileSession(cls.test_instance())


class InMemoryProfileSession(ProfileSession):
    """An active connection to the profile management backend."""

    def __init__(self, profile: Profile):
        """Create a new InMemoryProfileSession instance."""
        context = profile.context.start_scope("session")
        context.injector.bind_instance(BaseStorage, STORAGE_CLASS(self))
        context.injector.bind_provider(BaseWallet, WALLET_CLASS(self))
        super().__init__(profile=profile, context=context)

    @property
    def storage(self) -> BaseStorage:
        """Get the `BaseStorage` implementation (specific to in-memory profile)."""
        return self._context.inject(BaseStorage)

    @property
    def wallet(self) -> BaseWallet:
        """Get the `BaseWallet` implementation (specific to in-memory profile)."""
        return self._context.inject(BaseWallet)
