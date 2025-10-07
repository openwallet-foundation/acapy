"""Common utilities for AnonCreds route handlers."""

from aiohttp import web

from ....admin.request_context import AdminRequestContext
from ....core.profile import Profile
from ....utils.profiles import is_not_anoncreds_profile_raise_web_exception
from ...issuer import AnonCredsIssuerError
from ...revocation import AnonCredsRevocation


async def get_revocation_registry_definition_or_404(
    request: web.BaseRequest,
) -> tuple[AnonCredsRevocation, str]:
    """Common utility for getting revocation registry definition with error handling.

    Args:
        request: The aiohttp request object

    Returns:
        Tuple of (AnonCredsRevocation instance, rev_reg_id) after validation

    Raises:
        web.HTTPNotFound: If the revocation registry definition is not found
        web.HTTPInternalServerError: If there's an error retrieving the definition

    """
    context: AdminRequestContext = request["context"]
    profile = context.profile

    is_not_anoncreds_profile_raise_web_exception(profile)

    rev_reg_id = request.match_info["rev_reg_id"]
    try:
        revocation = AnonCredsRevocation(profile)
        rev_reg_def = await revocation.get_created_revocation_registry_definition(
            rev_reg_id
        )
        if rev_reg_def is None:
            raise web.HTTPNotFound(reason=f"Rev reg def with id {rev_reg_id} not found")
    except AnonCredsIssuerError as e:
        raise web.HTTPInternalServerError(reason=str(e)) from e

    return revocation, rev_reg_id


async def get_request_body_with_profile_check(
    request: web.BaseRequest,
) -> tuple[AdminRequestContext, Profile, dict, dict]:
    """Common utility for extracting request body with profile validation.

    Args:
        request: The aiohttp request object

    Returns:
        Tuple of (context, profile, body, options)

    """
    context: AdminRequestContext = request["context"]
    profile = context.profile

    is_not_anoncreds_profile_raise_web_exception(profile)

    body = await request.json()
    options = body.get("options", {})

    return context, profile, body, options
