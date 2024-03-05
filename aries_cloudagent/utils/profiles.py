"""Profile utilities."""

import json

from aiohttp import web

from ..anoncreds.error_messages import ANONCREDS_PROFILE_REQUIRED_MSG
from ..askar.profile_anon import AskarAnoncredsProfile
from ..core.profile import Profile
from ..multitenant.manager import MultitenantManager
from ..storage.base import BaseStorageSearch
from ..wallet.models.wallet_record import WalletRecord


def is_anoncreds_profile_raise_web_exception(profile: Profile) -> None:
    """Raise a web exception when the supplied profile is anoncreds."""
    if isinstance(profile, AskarAnoncredsProfile):
        raise web.HTTPForbidden(
            reason="Interface not supported for an anoncreds profile"
        )


def is_not_anoncreds_profile_raise_web_exception(profile: Profile) -> None:
    """Raise a web exception when the supplied profile is anoncreds."""
    if not isinstance(profile, AskarAnoncredsProfile):
        raise web.HTTPForbidden(reason=ANONCREDS_PROFILE_REQUIRED_MSG)


def subwallet_type_not_same_as_base_wallet_raise_web_exception(
    base_wallet_type: str, sub_wallet_type: str
) -> None:
    """Raise a web exception when the subwallet type is not the same as the base wallet type."""  # noqa: E501
    if base_wallet_type != sub_wallet_type:
        raise web.HTTPForbidden(
            reason="Subwallet type must be the same as the base wallet type"
        )


async def get_subwallet_profiles_from_storage(root_profile: Profile) -> list[Profile]:
    """Get subwallet profiles from storage."""
    subwallet_profiles = []
    base_storage_search = root_profile.inject(BaseStorageSearch)
    search_session = base_storage_search.search_records(
        type_filter=WalletRecord.RECORD_TYPE, page_size=10
    )
    while search_session._done is False:
        wallet_storage_records = await search_session.fetch()
        for wallet_storage_record in wallet_storage_records:
            wallet_record = WalletRecord.from_storage(
                wallet_storage_record.id,
                json.loads(wallet_storage_record.value),
            )
            subwallet_profiles.append(
                await MultitenantManager(root_profile).get_wallet_profile(
                    base_context=root_profile.context,
                    wallet_record=wallet_record,
                )
            )
    return subwallet_profiles
