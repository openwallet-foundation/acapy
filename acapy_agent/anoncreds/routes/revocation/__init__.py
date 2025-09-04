"""AnonCreds revocation routes."""

from ....messaging.models.openapi import OpenAPISchema

REVOCATION_TAG_TITLE = "AnonCreds - Revocation"


class AnonCredsRevocationModuleResponseSchema(OpenAPISchema):
    """Response schema for Revocation Module."""


__all__ = ["REVOCATION_TAG_TITLE", "AnonCredsRevocationModuleResponseSchema"]
