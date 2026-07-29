"""Helpers for reading request-scoped auth context safely.

These helpers support both:

1) Preferred request metadata (``AdminRequestContext.metadata``), and
2) Request-scoped settings fallback for compatibility.
"""

from collections.abc import Mapping
from typing import Any, Optional

AUTH_SCOPES_SETTING = "auth.scopes"
AUTH_SUBJECT_SETTING = "auth.subject"
AUTH_WALLET_ID_SETTING = "auth.wallet_id"


def _get_context_settings(context: Any) -> Mapping[str, Any]:
    settings = getattr(context, "settings", None)
    if isinstance(settings, Mapping):
        return settings
    return {}


def get_auth_metadata(context: Any) -> dict:
    """Return auth metadata when available, else an empty dict."""
    metadata = getattr(context, "metadata", None)
    if isinstance(metadata, dict):
        return metadata
    return {}


def has_auth_scopes(context: Any) -> bool:
    """Whether auth scopes are present on the request context."""
    metadata = get_auth_metadata(context)
    if "scopes" in metadata:
        return True
    settings = _get_context_settings(context)
    return AUTH_SCOPES_SETTING in settings


def get_auth_scopes(context: Any) -> set[str]:
    """Return normalized auth scopes from metadata or request settings."""
    metadata = get_auth_metadata(context)
    raw_scopes = metadata.get("scopes")
    if raw_scopes is None:
        raw_scopes = _get_context_settings(context).get(AUTH_SCOPES_SETTING, ())

    if isinstance(raw_scopes, str):
        return set(raw_scopes.split())
    if isinstance(raw_scopes, (set, list, tuple, frozenset)):
        return {scope for scope in raw_scopes if isinstance(scope, str)}
    return set()


def get_auth_subject(context: Any) -> Optional[str]:
    """Return token subject claim from metadata or request settings."""
    metadata = get_auth_metadata(context)
    subject = metadata.get("sub")
    if subject is None:
        subject = _get_context_settings(context).get(AUTH_SUBJECT_SETTING)
    return subject if isinstance(subject, str) else None


def get_auth_wallet_id(context: Any) -> Optional[str]:
    """Return request wallet id from metadata or request settings."""
    metadata = get_auth_metadata(context)
    wallet_id = metadata.get("wallet_id")
    if wallet_id is None:
        wallet_id = _get_context_settings(context).get(AUTH_WALLET_ID_SETTING)
    return wallet_id if isinstance(wallet_id, str) else None


def has_auth_wallet_id(context: Any) -> bool:
    """Whether request context carries a wallet_id claim."""
    return bool(get_auth_wallet_id(context))
