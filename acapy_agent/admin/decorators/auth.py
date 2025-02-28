"""Authentication decorators for the admin API."""

import functools
import re
from typing import List, Optional, Pattern

from aiohttp import web

from ...utils import general as general_utils
from ..request_context import AdminRequestContext


def admin_authentication(handler):
    """Decorator to require authentication via admin API key.

    The decorator will check for a valid x-api-key header and
    reject the request if it is missing or invalid.
    If the agent is running in insecure mode, the request will be allowed without a key.
    """

    @functools.wraps(handler)
    async def admin_auth(request):
        context: AdminRequestContext = request["context"]
        profile = context.profile
        header_admin_api_key = request.headers.get("x-api-key")
        valid_key = general_utils.const_compare(
            profile.settings.get("admin.admin_api_key"), header_admin_api_key
        )
        insecure_mode = bool(profile.settings.get("admin.admin_insecure_mode"))

        # We have to allow OPTIONS method access to paths without a key since
        # browsers performing CORS requests will never include the original
        # x-api-key header from the method that triggered the preflight
        # OPTIONS check.
        if insecure_mode or valid_key or (request.method == "OPTIONS"):
            return await handler(request)
        else:
            raise web.HTTPUnauthorized(
                reason="API Key invalid or missing",
                text="API Key invalid or missing",
            )

    return admin_auth


def tenant_authentication(handler):
    """Decorator to enable non-admin authentication.

    The decorator will:
    - check for a valid bearer token in the Autorization header if running
    in multi-tenant mode
    - check for a valid x-api-key header if running in single-tenant mode
    - check if the base wallet has access to the requested path if running
    in multi-tenant mode
    """

    @functools.wraps(handler)
    async def tenant_auth(request):
        context: AdminRequestContext = request["context"]
        profile = context.profile
        authorization_header = request.headers.get("Authorization")
        header_admin_api_key = request.headers.get("x-api-key")
        valid_key = general_utils.const_compare(
            profile.settings.get("admin.admin_api_key"), header_admin_api_key
        )
        insecure_mode = bool(profile.settings.get("admin.admin_insecure_mode"))
        multitenant_enabled = profile.settings.get("multitenant.enabled")
        base_wallet_routes = profile.settings.get("multitenant.base_wallet_routes")
        base_wallet_allowed_route = _base_wallet_route_access(
            [base_wallet_routes]
            if isinstance(base_wallet_routes, str)
            else base_wallet_routes,
            request.path,
        )

        # CORS fix: allow OPTIONS method access to paths without a token
        if (
            (multitenant_enabled and authorization_header)
            or (not multitenant_enabled and valid_key)
            or (multitenant_enabled and valid_key and base_wallet_allowed_route)
            or (insecure_mode and not multitenant_enabled)
            or request.method == "OPTIONS"
        ):
            return await handler(request)
        else:
            auth_mode = "Authorization token" if multitenant_enabled else "API key"
            raise web.HTTPUnauthorized(
                reason=f"{auth_mode} missing or invalid",
                text=f"{auth_mode} missing or invalid",
            )

    return tenant_auth


def _base_wallet_route_access(additional_routes: List[str], request_path: str) -> bool:
    """Check if request path matches additional routes."""
    additional_routes_pattern = (
        _build_additional_routes_pattern(additional_routes) if additional_routes else None
    )
    return _matches_additional_routes(additional_routes_pattern, request_path)


def _build_additional_routes_pattern(pattern_list: List[str]) -> Optional[Pattern]:
    """Build pattern from space delimited list of paths."""
    # create array and add word boundary to avoid false positives
    all_paths = []
    for pattern in pattern_list:
        paths = pattern.split(" ")
        all_paths = all_paths + paths
    return re.compile("^((?:)" + "|".join(all_paths) + ")$")


def _matches_additional_routes(pattern: Pattern, path: str) -> bool:
    """Matches request path to provided pattern."""
    if pattern and path:
        return bool(pattern.match(path))
    return False
