"""Manage Indy-SDK profile interaction."""

from typing import Optional, Type

from ...config.error import InjectorError
from ...core.profile import Profile, ProfileSession, InjectType
from ...storage.base import BaseStorage
from ...storage.indy import IndyStorage
from ...wallet.base import BaseWallet
from ...wallet.indy import IndyWallet

from ..holder import IndyHolder
from ..issuer import IndyIssuer
from ..verifier import IndyVerifier

from .issuer import IndySdkIssuer
from .holder import IndySdkHolder
from .verifier import IndySdkVerifier
from .wallet_setup import IndyOpenWallet

TYPE_MAP = {
    BaseStorage: IndyStorage,
    BaseWallet: IndyWallet,
    IndyHolder: IndySdkHolder,
    IndyIssuer: IndySdkIssuer,
    IndyVerifier: IndySdkVerifier,
}


class IndyProfile(Profile):
    """Provide access to Indy profile interaction methods."""

    def __init__(self, wallet: IndyOpenWallet):
        """Create a new IndyProfile instance."""
        self.wallet = wallet

    @property
    def backend(self) -> str:
        """Accessor for the backend implementation name."""
        return "indy"

    @property
    def name(self) -> str:
        """Accessor for the profile name."""
        return self.wallet.name

    async def start_session(self) -> "ProfileSession":
        """Start a new interactive session with no transaction support requested."""
        return IndyProfileSession(self.wallet)

    async def start_transaction(self) -> "ProfileSession":
        """
        Start a new interactive session with commit and rollback support.

        If the current backend does not support transactions, then commit
        and rollback operations of the session will not have any effect.
        """
        return IndyProfileSession(self.wallet)


class IndyProfileSession(ProfileSession):
    """An active connection to the profile management backend."""

    def __init__(self, wallet: IndyOpenWallet):
        """Create a new IndyProfileSession instance."""
        self.wallet = wallet

    def inject(
        self, base_cls: Type[InjectType], required: bool = True
    ) -> Optional[InjectType]:
        """Get an instance of a defined interface base class tied to this session."""
        if base_cls in TYPE_MAP:
            return TYPE_MAP[base_cls](self.wallet)
        if required:
            raise InjectorError(
                "No instance provided for class: {}".format(base_cls.__name__)
            )
