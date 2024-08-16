"""Class for paginated query parameters."""

from typing import Tuple

from aiohttp.web import BaseRequest
from marshmallow import fields
from marshmallow.validate import OneOf, Range

from ...messaging.models.openapi import OpenAPISchema
from ...storage.base import DEFAULT_PAGE_SIZE, MAXIMUM_PAGE_SIZE


class PaginatedQuerySchema(OpenAPISchema):
    """Parameters for paginated queries."""

    limit = fields.Int(
        required=False,
        load_default=DEFAULT_PAGE_SIZE,
        validate=Range(min=1, max=MAXIMUM_PAGE_SIZE),
        metadata={"description": "Number of results to return", "example": 50},
    )
    offset = fields.Int(
        required=False,
        load_default=0,
        validate=Range(min=0),
        metadata={"description": "Offset for pagination", "example": 0},
    )
    order_by = fields.Str(
        required=False,
        load_default=None,
        dump_only=True,  # Hide from schema by making it dump-only
        load_only=True,  # Ensure it can still be loaded/validated
        validate=OneOf(["id"]),  # Example of possible fields
        metadata={"description": "Order results in descending order if true"},
        error_messages={"validator_failed": "Ordering only support for column `id`"},
    )
    descending = fields.Bool(
        required=False,
        load_default=False,
        metadata={"description": "Order results in descending order if true"},
    )


def get_limit_offset(request: BaseRequest) -> Tuple[int, int]:
    """Read the limit and offset query parameters from a request as ints, with defaults.

    Args:
        request: aiohttp request object

    Returns:
        A tuple of the limit and offset values
    """

    limit = int(request.query.get("limit", DEFAULT_PAGE_SIZE))
    offset = int(request.query.get("offset", 0))
    return limit, offset
