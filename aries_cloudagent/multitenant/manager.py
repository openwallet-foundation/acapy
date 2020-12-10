"""Manager for multitenancy."""

import jwt
from typing import List, Optional, cast

from ..core.profile import (
    Profile,
    ProfileManager,
    ProfileManagerProvider,
    ProfileSession,
)
from ..config.wallet import wallet_config as configure_wallet
from ..config.injection_context import InjectionContext
from ..wallet.models.wallet_record import WalletRecord
from ..core.error import BaseError
from ..indy.sdk.profile import IndySdkProfile
from ..protocols.routing.v1_0.manager import RouteNotFoundError, RoutingManager
from ..transport.wire_format import BaseWireFormat

from .error import WalletKeyMissingError


class MultitenantManagerError(BaseError):
    """Generic multitenant error."""


class MultitenantManager:
    """Class for handling multitenancy."""

    def __init__(self, profile: Profile):
        """Initialize multitenant Manager.

        Args:
            profile: The profile for this manager
        """
        self._profile = profile
        if not profile:
            raise MultitenantManagerError("Missing profile")

    @property
    def profile(self) -> Profile:
        """
        Accessor for the current profile.

        Returns:
            The profile for this manager

        """
        return self._profile

    async def _wallet_name_exists(
        self, session: ProfileSession, wallet_name: str
    ) -> bool:
        """
        Check whether wallet with specified wallet name already exists.

        Besides checking for wallet records, it will also check if the base wallet

        Args:
            session: The profile session to use
            wallet_name: the wallet name to check for

        Returns:
            bool: Whether the wallet name already exists

        """
        # wallet_name is same as base wallet name
        if session.settings.get("wallet.name") == wallet_name:
            return True

        # subwallet record exists, we assume the wallet actually exists
        wallet_records = await WalletRecord.query(session, {"wallet_name": wallet_name})
        if len(wallet_records) > 0:
            return True

        return False

    def get_wallet_context(
        self,
        base_context: InjectionContext,
        wallet_record: WalletRecord,
        extra_settings: dict = {},
    ) -> InjectionContext:
        """Get the context for a wallet record.

        Args:
            base_context: Base context to extend from
            wallet_record: Wallet record to get the context for
            extra_settings: Any extra context settings

        Returns:
            InjectionContext: Context for the wallet record

        """
        context = base_context.copy()
        # MTODO: remove base wallet settings
        context.settings = context.settings.extend(
            wallet_record.get_config_as_settings()
        ).extend(extra_settings)

        # MTODO: caching
        # MTODO: context is passed to constructor of provider, if we can avoid
        # that we don't need to rebind the provider each time
        context.injector.bind_provider(ProfileManager, ProfileManagerProvider(context))

        return context

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
        context = self.get_wallet_context(base_context, wallet_record, extra_settings)
        profile, _ = await configure_wallet(context, provision=provision)

        return profile

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

        async with self.profile.session() as session:
            # Check if the wallet name already exists to avoid indy wallet errors
            if wallet_name and await self._wallet_name_exists(session, wallet_name):
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

            await wallet_record.save(session)

        profile = await self.get_wallet_profile(
            self.profile.context,
            wallet_record,
            {"wallet.key": wallet_key},
            provision=True,
        )

        await profile.close()
        del profile

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
        async with self.profile.session() as session:
            wallet = cast(
                WalletRecord,
                await WalletRecord.retrieve_by_id(session, wallet_id),
            )

            wallet_key = wallet_key or wallet.wallet_config.get("key")

            # MTODO: make wallet key required
            if not wallet.is_managed and not wallet_key:
                raise WalletKeyMissingError("Missing key to open wallet")

            profile = await self.get_wallet_profile(
                session.context,
                wallet,
                {"wallet.key": wallet_key},
            )

            # MTODO: add remove method to base profile
            # Remove the actual wallet
            if isinstance(profile, IndySdkProfile):
                profile.opened.config.auto_remove = True
                await profile.opened.close()

            # MTODO: delete route records
            await wallet.delete_record(session)

    async def add_wallet_route(
        self, wallet_id: str, recipient_key: str
    ) -> List[WalletRecord]:
        """
        Add a wallet route to map incoming messages to specific subwallets.

        Args:
            wallet_id: The wallet id the key corresponds to
            recipient_key: The recipient key belonging to the wallet
        """

        async with self.profile.session() as session:
            routing_mgr = RoutingManager(session)

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
        jwt_secret = self.profile.settings.get("multitenant.jwt_secret")

        if not wallet_record.is_managed:
            if not wallet_key:
                raise WalletKeyMissingError()

            jwt_payload["wallet_key"] = wallet_key

        token = jwt.encode(jwt_payload, jwt_secret).decode()

        return token

    async def _get_wallet_by_key(
        self, session: ProfileSession, recipient_key: str
    ) -> Optional[WalletRecord]:
        """Get the wallet record associated with the recipient key.

        Args:
            session: The profile session to use
            recipient_key: The recipient key
        Returns:
            Wallet record associated with the recipient key
        """
        routing_mgr = RoutingManager(session)

        try:
            routing_record = await routing_mgr.get_recipient(recipient_key)
            wallet = await WalletRecord.retrieve_by_id(
                session, routing_record.wallet_id
            )

            return wallet
        except (RouteNotFoundError):
            pass

    async def get_wallets_by_message(
        self, message_body, wire_format: BaseWireFormat = None
    ) -> List[WalletRecord]:
        """Get the wallet records associated with the message boy.

        Args:
            message_body: The body of the message
            wire_format: Wire format to use for recipient detection

        Returns:
            Wallet records associated with the message body

        """
        async with self.profile.session() as session:
            wire_format = wire_format or session.inject(BaseWireFormat)

            if not wire_format:
                raise MultitenantManagerError(
                    "Unable to detect recipient keys without wire formats"
                )

            recipient_keys = wire_format.get_recipient_keys(message_body)
            wallets = []

            for key in recipient_keys:
                wallet = await self._get_wallet_by_key(session, key)

                if wallet:
                    wallets.append(wallet)
