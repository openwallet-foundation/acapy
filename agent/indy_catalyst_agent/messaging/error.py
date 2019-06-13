"""Messaging-related error classes and codes."""

from ..error import BaseError


class MessageParseError(BaseError):
    """Message parse error."""

    error_code = "message_parse_error"


class MessagePrepareError(BaseError):
    """Message preparation error."""

    error_code = "message_prepare_error"
