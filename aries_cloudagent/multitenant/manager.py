"""Manager for multitenancy."""

import jwt
from typing import List

from ..wallet.models.wallet_record import WalletRecord
from ..config.injection_context import InjectionContext
from ..core.error import BaseError
from ..wallet.indy import IndyWallet
from ..protocols.routing.v1_0.manager import RouteNotFoundError, RoutingManager

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

    async def wallet_name_exists(self, wallet_name: str) -> bool:
        """
        Check whether wallet with specified wallet name already exists.

        Besides checking for wallet records, it will also check if the base wallet

        Args:
            wallet_name: the wallet name to check for

        Returns:
            bool: Whether the wallet name already exists

        """
        # wallet_name is same as base wallet name
        if self.context.settings.get("wallet.name") == wallet_name:
            return True

        # subwallet record exists, we assume the wallet actually exists
        wallet_records = await WalletRecord.query(
            self.context, {"wallet_name": wallet_name}
        )
        if len(wallet_records) > 0:
            return True

        return False

    async def create_wallet(
        self, wallet_config: dict, key_management_mode: str
    ) -> WalletRecord:
        """Create new wallet and wallet record.

        Args:
            wallet_config: The wallet config for the wallet to create
            key_management_mode: The mode to use for key management. Either "unmanaged"
                to not store the wallet key, or "managed" to store the wallet key

        Raises:
            MultitenantManagerError: If the wallet name already exists

        Returns:
            WalletRecord: The newly created wallet record

        """
        wallet_key = wallet_config.get("key")
        wallet_name = wallet_config.get("name")

        # Check if the wallet name already exists to avoid indy wallet errors
        if wallet_name and await self.wallet_name_exists(wallet_name):
            raise MultitenantManagerError(
                f"Wallet with name {wallet_name} already exists"
            )

        # In unmanaged mode we don't want to store the wallet key
        if key_management_mode == WalletRecord.MODE_UNMANAGED:
            wallet_config = {k: v for k, v in wallet_config.items() if k != "key"}

        # create and store wallet record
        wallet_record = WalletRecord(
            wallet_config=wallet_config,
            key_management_mode=key_management_mode,
        )
        await wallet_record.save(self.context)

        # this creates the actual wallet
        # MTODO: override wallet properties that shouldn't be set
        # e.g. it shouldn't take the base wallet name if none is provided
        await wallet_record.get_instance(self.context, {"key": wallet_key})

        return wallet_record

    async def remove_wallet(self, wallet_id: str, wallet_key: str = None):
        """Remove the wallet with specified wallet id.

        Args:
            wallet_id: The wallet id of the wallet record
            wallet_key: The wallet key to open the wallet.
                Only required for "unmanaged" wallets

        Raises:
            WalletKeyMissingError: If the wallet key is missing.
                Only thrown for "unmanaged" wallets

        """
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
        await wallet_instance.close()

        # Remove the actual wallet
        if wallet_instance.type == IndyWallet.type:
            await wallet_instance.remove()

        await wallet_record.delete_record(self.context)

    async def add_wallet_route(
        self, wallet_id: str, recipient_key: str
    ) -> List[WalletRecord]:
        """
        Add a wallet route to map incoming messages to specific subwallets.

        Args:
            wallet_id: The wallet id the key corresponds to
            recipient_key: The recipient key belonging to the wallet
        """

        routing_mgr = RoutingManager(self.context)

        await routing_mgr.create_route_record(
            recipient_key=recipient_key, internal_wallet_id=wallet_id
        )

    async def create_auth_token(
        self, wallet_record: WalletRecord, wallet_key: str = None
    ) -> str:
        """Create JWT auth token for specified wallet record.

        Args:
            wallet_record: The wallet record to create the token for
            wallet_key: The wallet key to include in the token.
                Only required for "unmanaged" wallets

        Raises:
            WalletKeyMissingError: If the wallet key is missing.
                Only thrown for "unmanaged" wallets

        Returns:
            str: JWT auth token

        """
        jwt_payload = {"wallet_id": wallet_record.wallet_record_id}
        jwt_secret = self.context.settings.get("multitenant.jwt_secret")

        if wallet_record.key_management_mode == WalletRecord.MODE_UNMANAGED:
            if not wallet_key:
                raise WalletKeyMissingError()

            jwt_payload["wallet_key"] = wallet_key

        token = jwt.encode(jwt_payload, jwt_secret).decode()

        return token

    async def get_wallets_by_recipient_keys(
        self, recipient_keys: List[str]
    ) -> List[WalletRecord]:
        """Get wallet records associated with recipient keys.

        Args:
            recipient_keys: List of recipient keys
        Returns:
            list of wallet records associated with the recipient keys
        """

        routing_mgr = RoutingManager(self.context)
        wallet_records = []

        for recipient_key in recipient_keys:
            try:
                routing_record = await routing_mgr.get_recipient(recipient_key)

                # MTODO: Should not be possible that wallet_id is None here
                if routing_record.wallet_id:
                    wallet_record = await WalletRecord.retrieve_by_id(
                        self.context, routing_record.wallet_id
                    )
                    wallet_records.append(wallet_record)
            except (RouteNotFoundError):
                pass

        return wallet_records
