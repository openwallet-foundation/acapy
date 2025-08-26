"""Common components for AnonCreds routes.

This package contains shared utilities, schema mixins, and test fixtures
used across different route modules in the AnonCreds system.
"""

from .schemas import (
    CredRevRecordQueryStringMixin,
    EndorserOptionsSchema,
    RevocationIdsDictMixin,
    RevRegIdMatchInfoMixin,
    SchemaQueryFieldsMixin,
)
from .testing import (
    BaseAnonCredsRouteTestCase,
    BaseAnonCredsRouteTestCaseWithOutbound,
    create_mock_request,
    create_standard_rev_reg_def,
    create_standard_rev_reg_def_value,
)
from .utils import (
    get_request_body_with_profile_check,
    get_revocation_registry_definition_or_404,
)

__all__ = [
    # Schema mixins and definitions
    "EndorserOptionsSchema",
    "SchemaQueryFieldsMixin",
    "CredRevRecordQueryStringMixin",
    "RevRegIdMatchInfoMixin",
    "RevocationIdsDictMixin",
    # Route utilities
    "get_revocation_registry_definition_or_404",
    "get_request_body_with_profile_check",
    # Test fixtures and data
    "BaseAnonCredsRouteTestCase",
    "BaseAnonCredsRouteTestCaseWithOutbound",
    "create_mock_request",
    "create_standard_rev_reg_def",
    "create_standard_rev_reg_def_value",
]
