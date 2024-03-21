"""Profile utilities."""

from aiohttp import web

from ..anoncreds.error_messages import ANONCREDS_PROFILE_REQUIRED_MSG
from ..askar.profile_anon import AskarAnoncredsProfile
from ..core.profile import Profile


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
