"""Manager for askar profile multitenancy mode."""

from typing import Iterable, Optional, cast
from ..core.profile import (
    Profile,
)
from ..config.wallet import wallet_config
from ..config.injection_context import InjectionContext
from ..wallet.models.wallet_record import WalletRecord
from ..askar.profile import AskarProfile
from ..multitenant.base import BaseMultitenantManager


class AskarProfileMultitenantManager(BaseMultitenantManager):
    """Class for handling askar profile multitenancy."""

    DEFAULT_MULTITENANT_WALLET_NAME = "multitenant_sub_wallet"

    def __init__(self, profile: Profile, multitenant_profile: AskarProfile = None):
        """Initialize askar profile multitenant Manager.

        Args:
            profile: The base profile for this manager
        """
        super().__init__(profile)
        self._multitenant_profile: Optional[AskarProfile] = multitenant_profile

    @property
    def open_profiles(self) -> Iterable[Profile]:
        """Return iterator over open profiles.

        Only the core multitenant profile is considered open.
        """
        if self._multitenant_profile:
            yield self._multitenant_profile

    async def get_wallet_profile(
        self,
        base_context: InjectionContext,
        wallet_record: WalletRecord,
        extra_settings: dict = {},
        *,
        provision=False,
    ) -> Profile:
        """Get Askar profile for a wallet record.

        An object of type AskarProfile is returned but this should not be
        confused with the underlying profile mechanism provided by Askar that
        enables multiple "profiles" to share a wallet. Usage of this mechanism
        is what causes this implementation of BaseMultitenantManager.get_wallet_profile
        to look different from others, especially since no explicit clean up is
        required for profiles that are no longer in use.

        Args:
            base_context: Base context to extend from
            wallet_record: Wallet record to get the context for
            extra_settings: Any extra context settings

        Returns:
            Profile: Profile for the wallet record

        """
        if not self._multitenant_profile:
            multitenant_wallet_name = base_context.settings.get(
                "multitenant.wallet_name", self.DEFAULT_MULTITENANT_WALLET_NAME
            )
            context = base_context.copy()
            sub_wallet_settings = {
                "wallet.recreate": False,
                "wallet.seed": None,
                "wallet.rekey": None,
                "wallet.id": None,
                "wallet.name": multitenant_wallet_name,
                "wallet.type": "askar",
                "mediation.open": None,
                "mediation.invite": None,
                "mediation.default_id": None,
                "mediation.clear": None,
                "auto_provision": True,
            }
            context.settings = context.settings.extend(sub_wallet_settings)

            profile, _ = await wallet_config(context, provision=False)
            self._multitenant_profile = cast(AskarProfile, profile)

        profile_context = self._multitenant_profile.context.copy()

        if provision:
            await self._multitenant_profile.store.create_profile(
                wallet_record.wallet_id
            )

        extra_settings = {
            "admin.webhook_urls": self.get_webhook_urls(base_context, wallet_record),
            "wallet.askar_profile": wallet_record.wallet_id,
        }

        profile_context.settings = profile_context.settings.extend(
            wallet_record.settings
        ).extend(extra_settings)

        assert self._multitenant_profile.opened

        return AskarProfile(
            self._multitenant_profile.opened,
            profile_context,
            profile_id=wallet_record.wallet_id,
        )

    async def remove_wallet_profile(self, profile: Profile):
        """Remove the wallet profile instance.

        Args:
            profile: The wallet profile instance

        """
        await profile.remove()
