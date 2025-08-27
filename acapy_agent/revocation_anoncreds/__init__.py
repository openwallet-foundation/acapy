"""Backward compatibility imports for revocation_anoncreds module.

This module has been merged into the main anoncreds module.
Please update your imports to use the new location: acapy_agent.anoncreds.revocation
"""

import warnings

from ..anoncreds.models.issuer_cred_rev_record import (
    IssuerCredRevRecord,
    IssuerCredRevRecordSchemaAnonCreds,
)
from ..anoncreds.revocation.manager import RevocationManager, RevocationManagerError
from ..anoncreds.revocation.recover import (
    RevocRecoveryException,
    fetch_txns,
    generate_ledger_rrrecovery_txn,
)
from ..anoncreds.revocation.revocation import (
    AnonCredsRevocation,
    AnonCredsRevocationError,
)
from ..anoncreds.revocation.revocation_setup import DefaultRevocationSetup

# Issue deprecation warning
warnings.warn(
    "The 'revocation_anoncreds' module has been merged into the main 'anoncreds' module. "
    "Please update your imports to use 'acapy_agent.anoncreds.revocation' instead. "
    "This module will be removed in a future version.",
    DeprecationWarning,
    stacklevel=2,
)
__all__ = [
    "AnonCredsRevocation",
    "AnonCredsRevocationError",
    "DefaultRevocationSetup",
    "IssuerCredRevRecord",
    "IssuerCredRevRecordSchemaAnonCreds",
    "RevocRecoveryException",
    "RevocationManager",
    "RevocationManagerError",
    "fetch_txns",
    "generate_ledger_rrrecovery_txn",
]
