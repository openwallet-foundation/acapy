"""Manager for askar profile multitenancy mode."""

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

    DEFAULT_MULTIENANT_WALLET_NAME = "multitenant_sub_wallet"

    def __init__(self, profile: Profile):
        """Initialize askar profile multitenant Manager.

        Args:
            profile: The base profile for this manager
        """
        super().__init__(profile)

    async def get_wallet_profile(
        self,
        base_context: InjectionContext,
        wallet_record: WalletRecord,
        extra_settings: dict = {},
        *,
        provision=False,
    ) -> Profile:
        """Get Askar profile for a wallet record.

        Args:
            base_context: Base context to extend from
            wallet_record: Wallet record to get the context for
            extra_settings: Any extra context settings

        Returns:
            Profile: Profile for the wallet record

        """
        multitenant_wallet_name = (
            base_context.settings.get("multitenant.wallet_name")
            or self.DEFAULT_MULTIENANT_WALLET_NAME
        )

        if multitenant_wallet_name not in self._instances:
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
            self._instances[multitenant_wallet_name] = profile

        multitenant_wallet = self._instances[multitenant_wallet_name]
        profile_context = multitenant_wallet.context.copy()

        if provision:
            await multitenant_wallet.store.create_profile(wallet_record.wallet_id)

        extra_settings = {
            "admin.webhook_urls": self.get_webhook_urls(base_context, wallet_record),
            "wallet.askar_profile": wallet_record.wallet_id,
        }

        profile_context.settings = profile_context.settings.extend(
            wallet_record.settings
        ).extend(extra_settings)

        return AskarProfile(multitenant_wallet.opened, profile_context)

    async def remove_wallet_profile(self, profile: Profile):
        """Remove the wallet profile instance.

        Args:
            profile: The wallet profile instance

        """
        await profile.remove()
