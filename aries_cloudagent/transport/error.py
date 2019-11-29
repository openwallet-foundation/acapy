"""Transport-related error classes and codes."""

from ..error import BaseError


class TransportError(BaseError):
    """Base class for all transport errors."""


class WireFormatError(TransportError):
    """Base class for wire-format errors."""


class MessageParseError(WireFormatError):
    """Message parse error."""

    error_code = "message_parse_error"


class MessageEncodeError(WireFormatError):
    """Message encoding error."""

    error_code = "message_encode_error"
