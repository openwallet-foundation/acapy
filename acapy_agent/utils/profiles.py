"""Profile utilities."""

import json

from aiohttp import web

from ..anoncreds.error_messages import ANONCREDS_PROFILE_REQUIRED_MSG
from ..askar.profile_anon import AskarAnonCredsProfile
from ..core.profile import Profile
from ..multitenant.manager import MultitenantManager
from ..multitenant.single_wallet_askar_manager import SingleWalletAskarMultitenantManager
from ..storage.base import BaseStorageSearch
from ..wallet.models.wallet_record import WalletRecord


def is_anoncreds_profile_raise_web_exception(profile: Profile) -> None:
    """Raise a web exception when the supplied profile is anoncreds."""
    if isinstance(profile, AskarAnonCredsProfile):
        raise web.HTTPForbidden(reason="Interface not supported for an anoncreds profile")


def is_not_anoncreds_profile_raise_web_exception(profile: Profile) -> None:
    """Raise a web exception when the supplied profile is anoncreds."""
    if not isinstance(profile, AskarAnonCredsProfile):
        raise web.HTTPForbidden(reason=ANONCREDS_PROFILE_REQUIRED_MSG)


async def get_subwallet_profiles_from_storage(root_profile: Profile) -> list[Profile]:
    """Get subwallet profiles from storage."""
    subwallet_profiles = []
    base_storage_search = root_profile.inject(BaseStorageSearch)
    search_session = base_storage_search.search_records(
        type_filter=WalletRecord.RECORD_TYPE, page_size=10
    )
    if (
        root_profile.context.settings.get("multitenant.wallet_type")
        == "single-wallet-askar"
    ):
        manager = SingleWalletAskarMultitenantManager(root_profile)
    else:
        manager = MultitenantManager(root_profile)
    while search_session._done is False:
        wallet_storage_records = await search_session.fetch()
        for wallet_storage_record in wallet_storage_records:
            wallet_record = WalletRecord.from_storage(
                wallet_storage_record.id,
                json.loads(wallet_storage_record.value),
            )
            subwallet_profiles.append(
                await manager.get_wallet_profile(
                    base_context=root_profile.context,
                    wallet_record=wallet_record,
                )
            )
    return subwallet_profiles
