"""Manage in-memory profile interaction."""

from collections import OrderedDict
from typing import Any, Mapping

from ..config.injection_context import InjectionContext
from ..storage.base import BaseStorage
from ..utils.classloader import DeferLoad
from ..wallet.base import BaseWallet

from .profile import Profile, ProfileManager, ProfileSession

STORAGE_CLASS = DeferLoad("aries_cloudagent.storage.in_memory.InMemoryStorage")
WALLET_CLASS = DeferLoad("aries_cloudagent.wallet.in_memory.InMemoryWallet")


class InMemoryProfile(Profile):
    """
    Provide access to in-memory profile management.

    Used primarily for testing.
    """

    BACKEND_NAME = "in_memory"
    TEST_PROFILE_NAME = "test-profile"

    def __init__(self, *, context: InjectionContext = None, name: str = None):
        """Create a new InMemoryProfile instance."""
        global STORAGE_CLASS, WALLET_CLASS
        super().__init__(context=context, name=name)
        self.keys = {}
        self.local_dids = {}
        self.pair_dids = {}
        self.records = OrderedDict()

    def session(self) -> "ProfileSession":
        """Start a new interactive session with no transaction support requested."""
        return InMemoryProfileSession(self)

    def transaction(self) -> "ProfileSession":
        """
        Start a new interactive session with commit and rollback support.

        If the current backend does not support transactions, then commit
        and rollback operations of the session will not have any effect.
        """
        return InMemoryProfileSession(self)

    @classmethod
    def test_profile(cls) -> "InMemoryProfile":
        """Used in tests to create a standard InMemoryProfile."""
        return InMemoryProfile(name=InMemoryProfile.TEST_PROFILE_NAME)

    @classmethod
    def test_session(
        cls, settings: Mapping[str, Any] = None
    ) -> "InMemoryProfileSession":
        """Used in tests to quickly create InMemoryProfileSession."""
        return InMemoryProfileSession(cls.test_profile())


class InMemoryProfileSession(ProfileSession):
    """An active connection to the profile management backend."""

    def __init__(self, profile: Profile, *, settings: Mapping[str, Any] = None):
        """Create a new InMemoryProfileSession instance."""
        super().__init__(profile=profile, settings=settings)

    def _setup(self):
        """Create the session or transaction connection, if needed."""
        super()._setup()
        self._context.injector.bind_instance(BaseStorage, STORAGE_CLASS(self))
        self._context.injector.bind_provider(BaseWallet, WALLET_CLASS(self))

    @property
    def storage(self) -> BaseStorage:
        """Get the `BaseStorage` implementation (helper specific to in-memory profile)."""
        return self._context.inject(BaseStorage)

    @property
    def wallet(self) -> BaseWallet:
        """Get the `BaseWallet` implementation (helper specific to in-memory profile)."""
        return self._context.inject(BaseWallet)


class InMemoryProfileManager(ProfileManager):
    """Manager for producing in-memory wallet/storage implementation."""

    def __init__(self, context: InjectionContext):
        """Initialize the profile manager."""
        self._context = context
        self._instances = {}

    async def provision(self, config: Mapping[str, Any] = None) -> Profile:
        """Provision a new instance of a profile."""
        return InMemoryProfile(self._context, (config or {}).get("name"))

    async def open(self, config: Mapping[str, Any] = None) -> Profile:
        """Open an instance of an existing profile."""
        return await self.provision(config)
