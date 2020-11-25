"""Manager for multitenancy."""

from ..wallet.models.wallet_record import WalletRecord
from ..config.injection_context import InjectionContext
from ..core.error import BaseError
from ..wallet.indy import IndyWallet

from .error import WalletKeyMissingError


class MultitenantManagerError(BaseError):
    """Generic multitenant error."""


class MultitenantManager:
    """Class for handling multitenancy."""

    def __init__(self, context: InjectionContext):
        """Initialize multitenant Manager.

        Args:
            context: The context for this manager
        """
        if not context:
            raise MultitenantManagerError("Missing request context")

        self.context = context

    async def remove_wallet(self, wallet_id: str, wallet_key: str = None):
        wallet_record = await WalletRecord.retrieve_by_id(self.context, wallet_id)

        # Check if key is required and present
        if wallet_record.wallet_type == IndyWallet.type and not (
            wallet_key or wallet_record.wallet_config.get("key")
        ):
            raise WalletKeyMissingError("Missing key to open wallet")

        # MTODO: handle unable to open error
        wallet_instance = await wallet_record.get_instance(
            self.context, {"wallet.key": wallet_key} if wallet_key else {}
        )
        wallet_instance.close()

        # Remove the actual wallet
        if wallet_instance.type == IndyWallet.type:
            await wallet_instance.remove()

        await wallet_record.delete_record(self.context)