"""Manager for multitenancy."""

from abc import ABC, abstractmethod
from datetime import datetime
import logging
from typing import Iterable, List, Optional, cast, Tuple

import jwt

from ..config.injection_context import InjectionContext
from ..core.error import BaseError
from ..core.profile import Profile, ProfileSession
from ..protocols.coordinate_mediation.v1_0.manager import (
    MediationManager,
    MediationRecord,
)
from ..protocols.coordinate_mediation.v1_0.route_manager import RouteManager
from ..protocols.routing.v1_0.manager import RouteNotFoundError, RoutingManager
from ..protocols.routing.v1_0.models.route_record import RouteRecord
from ..storage.base import BaseStorage
from ..transport.wire_format import BaseWireFormat
from ..wallet.base import BaseWallet
from ..wallet.models.wallet_record import WalletRecord
from .error import WalletKeyMissingError

LOGGER = logging.getLogger(__name__)


class MultitenantManagerError(BaseError):
    """Generic multitenant error."""


class BaseMultitenantManager(ABC):
    """Base class for handling multitenancy."""

    def __init__(self, profile: Profile):
        """Initialize base multitenant Manager.

        Args:
            profile: The profile for this manager
        """
        self._profile = profile
        if not profile:
            raise MultitenantManagerError("Missing profile")

    @property
    @abstractmethod
    def open_profiles(self) -> Iterable[Profile]:
        """Return iterator over open profiles."""

    async def get_default_mediator(self) -> Optional[MediationRecord]:
        """Retrieve the default mediator used for subwallet routing.

        Returns:
            Optional[MediationRecord]: retrieved default mediator or None if not set

        """
        return await MediationManager(self._profile).get_default_mediator()

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

    def get_webhook_urls(
        self,
        base_context: InjectionContext,
        wallet_record: WalletRecord,
    ) -> list:
        """Get the webhook urls according to dispatch_type.

        Args:
            base_context: Base context to get base_webhook_urls
            wallet_record: Wallet record to get dispatch_type and webhook_urls
        Returns:
            webhook urls according to dispatch_type
        """
        wallet_id = wallet_record.wallet_id
        dispatch_type = wallet_record.wallet_dispatch_type
        subwallet_webhook_urls = wallet_record.wallet_webhook_urls or []
        base_webhook_urls = base_context.settings.get("admin.webhook_urls", [])

        if dispatch_type == "both":
            webhook_urls = list(set(base_webhook_urls) | set(subwallet_webhook_urls))
            if not webhook_urls:
                LOGGER.warning(
                    "No webhook URLs in context configuration "
                    f"nor wallet record {wallet_id}, but wallet record "
                    f"configures dispatch type {dispatch_type}"
                )
        elif dispatch_type == "default":
            webhook_urls = subwallet_webhook_urls
            if not webhook_urls:
                LOGGER.warning(
                    f"No webhook URLs in nor wallet record {wallet_id}, but "
                    f"wallet record configures dispatch type {dispatch_type}"
                )
        else:
            webhook_urls = base_webhook_urls

        return webhook_urls

    @abstractmethod
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

    async def create_wallet(
        self,
        settings: dict,
        key_management_mode: str,
    ) -> WalletRecord:
        """Create new wallet and wallet record.

        Args:
            settings: The context settings for this wallet
            key_management_mode: The mode to use for key management. Either "unmanaged"
                to not store the wallet key, or "managed" to store the wallet key

        Raises:
            MultitenantManagerError: If the wallet name already exists

        Returns:
            WalletRecord: The newly created wallet record

        """
        wallet_key = settings.get("wallet.key")
        wallet_name = settings.get("wallet.name")

        # base wallet context
        async with self._profile.session() as session:
            # Check if the wallet name already exists to avoid indy wallet errors
            if wallet_name and await self._wallet_name_exists(session, wallet_name):
                raise MultitenantManagerError(
                    f"Wallet with name {wallet_name} already exists"
                )

            # In unmanaged mode we don't want to store the wallet key
            if key_management_mode == WalletRecord.MODE_UNMANAGED:
                del settings["wallet.key"]
            # create and store wallet record
            wallet_record = WalletRecord(
                settings=settings, key_management_mode=key_management_mode
            )

            await wallet_record.save(session)
        try:
            # provision wallet
            profile = await self.get_wallet_profile(
                self._profile.context,
                wallet_record,
                {
                    "wallet.key": wallet_key,
                },
                provision=True,
            )

            # subwallet context
            async with profile.session() as session:
                wallet = session.inject(BaseWallet)
                public_did_info = await wallet.get_public_did()

            if public_did_info:
                await profile.inject(RouteManager).route_verkey(
                    profile, public_did_info.verkey
                )
        except Exception:
            await wallet_record.delete_record(session)
            raise

        return wallet_record

    async def update_wallet(
        self,
        wallet_id: str,
        new_settings: dict,
    ) -> WalletRecord:
        """Update an existing wallet record.

        Args:
            wallet_id: The wallet id of the wallet record
            new_settings: The context settings to be updated for this wallet

        Returns:
            WalletRecord: The updated wallet record

        """
        # update wallet_record
        async with self._profile.session() as session:
            wallet_record = await WalletRecord.retrieve_by_id(session, wallet_id)
            wallet_record.update_settings(new_settings)
            await wallet_record.save(session)

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
        async with self._profile.session() as session:
            wallet = cast(
                WalletRecord,
                await WalletRecord.retrieve_by_id(session, wallet_id),
            )

        wallet_key = wallet_key or wallet.wallet_key
        if wallet.requires_external_key and not wallet_key:
            raise WalletKeyMissingError("Missing key to open wallet")

        profile = await self.get_wallet_profile(
            self._profile.context,
            wallet,
            {"wallet.key": wallet_key},
        )

        await self.remove_wallet_profile(profile)

        # Remove all routing records associated with wallet
        async with self._profile.session() as session:
            storage = session.inject(BaseStorage)
            await storage.delete_all_records(
                RouteRecord.RECORD_TYPE, {"wallet_id": wallet.wallet_id}
            )

            await wallet.delete_record(session)

    @abstractmethod
    async def remove_wallet_profile(self, profile: Profile):
        """Remove the wallet profile instance.

        Args:
            profile: The wallet profile instance

        """

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
        iat = int(round(datetime.utcnow().timestamp()))

        jwt_payload = {"wallet_id": wallet_record.wallet_id, "iat": iat}
        jwt_secret = self._profile.settings.get("multitenant.jwt_secret")

        if wallet_record.requires_external_key:
            if not wallet_key:
                raise WalletKeyMissingError()

            jwt_payload["wallet_key"] = wallet_key

        token = jwt.encode(jwt_payload, jwt_secret, algorithm="HS256")

        # Store iat for verification later on
        wallet_record.jwt_iat = iat
        async with self._profile.session() as session:
            await wallet_record.save(session)

        return token

    def get_wallet_details_from_token(self, token: str) -> Tuple[str, str]:
        """Get the wallet_id and wallet_key from provided token."""
        jwt_secret = self._profile.context.settings.get("multitenant.jwt_secret")
        token_body = jwt.decode(token, jwt_secret, algorithms=["HS256"], leeway=1)
        wallet_id = token_body.get("wallet_id")
        wallet_key = token_body.get("wallet_key")
        return wallet_id, wallet_key

    async def get_wallet_and_profile(
        self, context: InjectionContext, wallet_id: str, wallet_key: str
    ) -> Tuple[WalletRecord, Profile]:
        """Get the wallet_record and profile associated with wallet id and key."""
        extra_settings = {}
        async with self._profile.session() as session:
            wallet = await WalletRecord.retrieve_by_id(session, wallet_id)
        if wallet.requires_external_key:
            if not wallet_key:
                raise WalletKeyMissingError()
            extra_settings["wallet.key"] = wallet_key
        profile = await self.get_wallet_profile(context, wallet, extra_settings)
        return (wallet, profile)

    async def get_profile_for_token(
        self, context: InjectionContext, token: str
    ) -> Profile:
        """Get the profile associated with a JWT header token.

        Args:
            context: The context to use for profile creation
            token: The token

        Raises:
            WalletKeyMissingError: If the wallet_key is missing for an unmanaged wallet
            InvalidTokenError: If there is an exception while decoding the token

        Returns:
            Profile associated with the token

        """
        jwt_secret = self._profile.context.settings.get("multitenant.jwt_secret")
        extra_settings = {}

        token_body = jwt.decode(token, jwt_secret, algorithms=["HS256"], leeway=1)

        wallet_id = token_body.get("wallet_id")
        wallet_key = token_body.get("wallet_key")
        iat = token_body.get("iat")

        async with self._profile.session() as session:
            wallet = await WalletRecord.retrieve_by_id(session, wallet_id)

        if wallet.requires_external_key:
            if not wallet_key:
                raise WalletKeyMissingError()

            extra_settings["wallet.key"] = wallet_key

        if wallet.jwt_iat and wallet.jwt_iat != iat:
            raise MultitenantManagerError("Token not valid")

        profile = await self.get_wallet_profile(context, wallet, extra_settings)

        return profile

    async def _get_wallet_by_key(self, recipient_key: str) -> Optional[WalletRecord]:
        """Get the wallet record associated with the recipient key.

        Args:
            recipient_key: The recipient key
        Returns:
            Wallet record associated with the recipient key
        """
        routing_mgr = RoutingManager(self._profile)

        try:
            routing_record = await routing_mgr.get_recipient(recipient_key)
            async with self._profile.session() as session:
                wallet = await WalletRecord.retrieve_by_id(
                    session, routing_record.wallet_id
                )

            return wallet
        except RouteNotFoundError:
            pass

    async def get_profile_for_key(
        self, context: InjectionContext, recipient_key: str
    ) -> Optional[Profile]:
        """Retrieve a wallet profile by recipient key."""
        wallet = await self._get_wallet_by_key(recipient_key)
        if not wallet:
            return None

        if wallet.requires_external_key:
            raise WalletKeyMissingError()

        return await self.get_wallet_profile(context, wallet)

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
        wire_format = wire_format or self._profile.inject(BaseWireFormat)

        recipient_keys = wire_format.get_recipient_keys(message_body)
        wallets = []

        for key in recipient_keys:
            wallet = await self._get_wallet_by_key(key)

            if wallet:
                wallets.append(wallet)

        return wallets
