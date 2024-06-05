"""Class for paginated query parameters."""

from marshmallow import fields

from aries_cloudagent.storage.base import DEFAULT_PAGE_SIZE, MAXIMUM_PAGE_SIZE

from ...messaging.models.openapi import OpenAPISchema


class PaginatedQuerySchema(OpenAPISchema):
    """Parameters for paginated queries."""

    limit = fields.Int(
        required=False,
        missing=DEFAULT_PAGE_SIZE,
        validate=lambda x: x > 0 and x <= MAXIMUM_PAGE_SIZE,
        metadata={"description": "Number of results to return", "example": 50},
        error_messages={
            "validator_failed": (
                "Value must be greater than 0 and "
                f"less than or equal to {MAXIMUM_PAGE_SIZE}"
            )
        },
    )
    offset = fields.Int(
        required=False,
        missing=0,
        validate=lambda x: x >= 0,
        metadata={"description": "Offset for pagination", "example": 0},
        error_messages={"validator_failed": "Value must be 0 or greater"},
    )
