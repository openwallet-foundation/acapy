"""Extract validation error messages from nested exceptions."""

from aiohttp.web import HTTPUnprocessableEntity
from marshmallow.exceptions import ValidationError


def extract_validation_error_message(exc: HTTPUnprocessableEntity) -> str:
    """Extract marshmallow error message from a nested UnprocessableEntity exception."""
    visited = set()
    current_exc = exc
    while current_exc and current_exc not in visited:
        visited.add(current_exc)
        if isinstance(current_exc, ValidationError):
            return current_exc.messages
        current_exc = current_exc.__cause__ or current_exc.__context__
    return exc.reason
