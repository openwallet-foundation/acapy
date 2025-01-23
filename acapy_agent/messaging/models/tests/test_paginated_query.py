import pytest
from marshmallow import ValidationError

from acapy_agent.storage.base import DEFAULT_PAGE_SIZE, MAXIMUM_PAGE_SIZE

from ..paginated_query import PaginatedQuerySchema


def test_paginated_query_schema_defaults():
    schema = PaginatedQuerySchema()
    result = schema.load({})
    assert result["limit"] == DEFAULT_PAGE_SIZE
    assert result["offset"] == 0


def test_paginated_query_schema_not_required():
    schema = PaginatedQuerySchema()
    result = schema.load({"limit": 10})
    assert result["limit"] == 10
    assert result["offset"] == 0

    result = schema.load({"offset": 5})
    assert result["limit"] == DEFAULT_PAGE_SIZE
    assert result["offset"] == 5


def test_paginated_query_schema_limit_validation():
    schema = PaginatedQuerySchema()

    # Valid limit
    result = schema.load({"limit": 1})
    assert result["limit"] == 1

    result = schema.load({"limit": MAXIMUM_PAGE_SIZE})
    assert result["limit"] == MAXIMUM_PAGE_SIZE

    # Invalid limit (less than 1)
    with pytest.raises(ValidationError) as exc_info:
        schema.load({"limit": 0})
    assert (
        f"Must be greater than or equal to 1 and less than or equal to {MAXIMUM_PAGE_SIZE}"
        in str(exc_info.value)
    )

    # Invalid limit (greater than MAXIMUM_PAGE_SIZE)
    with pytest.raises(ValidationError) as exc_info:
        schema.load({"limit": MAXIMUM_PAGE_SIZE + 1})
    assert (
        f"Must be greater than or equal to 1 and less than or equal to {MAXIMUM_PAGE_SIZE}"
        in str(exc_info.value)
    )


def test_paginated_query_schema_offset_validation():
    schema = PaginatedQuerySchema()

    # Valid offset
    result = schema.load({"offset": 0})
    assert result["offset"] == 0

    result = schema.load({"offset": 10})
    assert result["offset"] == 10

    # Invalid offset (less than 0)
    with pytest.raises(ValidationError) as exc_info:
        schema.load({"offset": -1})
    assert "Must be greater than or equal to 0." in str(exc_info.value)
