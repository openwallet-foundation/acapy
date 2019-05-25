"""Messaging-related error classes and codes."""

from ..error import BaseError


class MessageParseError(BaseError):
    """Message parse error."""

    error_code = "message_parse_error"
