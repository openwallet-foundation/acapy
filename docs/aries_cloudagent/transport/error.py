"""Transport-related error classes and codes."""

from ..core.error import BaseError


class TransportError(BaseError):
    """Base class for all transport errors."""


class WireFormatError(TransportError):
    """Base class for wire-format errors."""


class WireFormatParseError(WireFormatError):
    """Parse error when unpacking the wire format."""

    error_code = "message_parse_error"


class WireFormatEncodeError(WireFormatError):
    """Encoding error when packing the wire format."""

    error_code = "message_encode_error"


class RecipientKeysError(WireFormatError):
    """Extract recipient keys error."""
