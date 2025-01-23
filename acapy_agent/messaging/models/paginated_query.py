"""Class for paginated query parameters."""

from typing import Tuple

from aiohttp.web import BaseRequest
from marshmallow import fields
from marshmallow.validate import Range

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
