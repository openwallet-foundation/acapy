"""Manage in-memory profile interaction."""

from collections import OrderedDict
from typing import Optional, Type

from ...config.error import InjectorError
from ...core.profile import Profile, ProfileSession, InjectType
from ...storage.base import BaseStorage
from ...storage.in_memory import InMemoryStorage
from ...wallet.base import BaseWallet
from ...wallet.in_memory import InMemoryWallet

TYPE_MAP = {
    BaseStorage: InMemoryStorage,
    BaseWallet: InMemoryWallet,
}


class InMemoryProfile(Profile):
    """Provide access to in-memory profile interaction methods."""

    def __init__(self, name: str):
        """Create a new InMemoryProfile instance."""
        self.name = name
        self.keys = {}
        self.local_dids = {}
        self.pair_dids = {}
        self.records = OrderedDict()

    @property
    def backend(self) -> str:
        """Accessor for the backend implementation name."""
        return "in_memory"

    @property
    def name(self) -> str:
        """Accessor for the profile name."""
        return self._name

    async def start_session(self) -> "ProfileSession":
        """Start a new interactive session with no transaction support requested."""
        return InMemoryProfileSession(self)

    async def start_transaction(self) -> "ProfileSession":
        """
        Start a new interactive session with commit and rollback support.

        If the current backend does not support transactions, then commit
        and rollback operations of the session will not have any effect.
        """
        return InMemoryProfileSession(self)


class InMemoryProfileSession(ProfileSession):
    """An active connection to the profile management backend."""

    def __init__(self, profile: InMemoryProfile):
        """Create a new InMemoryProfileSession instance."""
        self.profile = profile

    def inject(
        self, base_cls: Type[InjectType], required: bool = True
    ) -> Optional[InjectType]:
        """Get an instance of a defined interface base class tied to this session."""
        if base_cls in TYPE_MAP:
            return TYPE_MAP[base_cls](self.profile)
        if required:
            raise InjectorError(
                "No instance provided for class: {}".format(base_cls.__name__)
            )
