"""Manager for multitenancy."""

from ..core.profile import (
    Profile,
)
from ..config.wallet import wallet_config
from ..config.injection_context import InjectionContext
from ..wallet.models.wallet_record import WalletRecord
from ..multitenant.base import BaseMultitenantManager


class MultitenantManager(BaseMultitenantManager):
    """Class for handling multitenancy."""

    def __init__(self, profile: Profile):
        """Initialize default multitenant Manager.

        Args:
            profile: The profile for this manager
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
        """Get profile for a wallet record.

        Args:
            base_context: Base context to extend from
            wallet_record: Wallet record to get the context for
            extra_settings: Any extra context settings

        Returns:
            Profile: Profile for the wallet record

        """
        wallet_id = wallet_record.wallet_id
        if wallet_id not in self._instances:
            # Extend base context
            context = base_context.copy()

            # Settings we don't want to use from base wallet
            reset_settings = {
                "wallet.recreate": False,
                "wallet.seed": None,
                "wallet.rekey": None,
                "wallet.name": None,
                "wallet.type": None,
                "mediation.open": None,
                "mediation.invite": None,
                "mediation.default_id": None,
                "mediation.clear": None,
            }
            extra_settings["admin.webhook_urls"] = self.get_webhook_urls(
                base_context, wallet_record
            )

            context.settings = (
                context.settings.extend(reset_settings)
                .extend(wallet_record.settings)
                .extend(extra_settings)
            )

            # MTODO: add ledger config
            profile, _ = await wallet_config(context, provision=provision)
            self._instances[wallet_id] = profile

        return self._instances[wallet_id]

    async def remove_wallet_profile(self, profile: Profile):
        """Remove the wallet profile instance.

        Args:
            profile: The wallet profile instance

        """
        wallet_id = profile.settings.get("wallet.id")
        del self._instances[wallet_id]
        await profile.remove()
