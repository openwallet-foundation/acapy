"""Manage Indy-SDK profile interaction."""

from ...config.provider import ClassProvider
from ...core.profile import Profile, ProfileSession
from ...storage.base import BaseStorage
from ...wallet.base import BaseWallet

from ..holder import IndyHolder
from ..issuer import IndyIssuer
from ..verifier import IndyVerifier

from .wallet_setup import IndyOpenWallet


class IndySdkProfile(Profile):
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
        return IndySdkProfileSession(self)

    async def start_transaction(self) -> "ProfileSession":
        """
        Start a new interactive session with commit and rollback support.

        If the current backend does not support transactions, then commit
        and rollback operations of the session will not have any effect.
        """
        return IndySdkProfileSession(self)


class IndySdkProfileSession(ProfileSession):
    """An active connection to the profile management backend."""

    def __init__(self, profile: IndySdkProfile):
        """Create a new IndySdkProfileSession instance."""
        context = profile.context.start_scope("session")
        context.injector.bind_provider(
            BaseStorage,
            ClassProvider("aries_cloudagent.storage.indy.IndyStorage", self.wallet),
        )
        context.injector.bind_provider(
            BaseWallet,
            ClassProvider("aries_cloudagent.wallet.indy.IndyWallet", self.wallet),
        )
        context.injector.bind_provider(
            IndyHolder,
            ClassProvider(
                "aries_cloudagent.indy.sdk.holder.IndySdkHolder", self.wallet
            ),
        )
        context.injector.bind_provider(
            IndyIssuer,
            ClassProvider(
                "aries_cloudagent.indy.sdk.issuer.IndySdkIssuer", self.wallet
            ),
        )
        context.injector.bind_provider(
            IndyVerifier,
            ClassProvider(
                "aries_cloudagent.indy.sdk.verifier.IndySdkVerifier", self.wallet
            ),
        )
        super().__init__(profile=profile, context=context)
