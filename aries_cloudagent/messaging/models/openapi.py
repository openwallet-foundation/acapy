"""Base class for OpenAPI artifact schema."""

from marshmallow import Schema, EXCLUDE


class OpenAPISchema(Schema):
    """Schema for OpenAPI artifacts: excluding unknown fields, not raising exception."""

    class Meta:
        """OpenAPISchema metadata."""

        model_class = None
        unknown = EXCLUDE
