"""JSON-LD messaging Exceptions."""

from ...core.error import BaseError


class BaseJSONLDMessagingError(BaseError):
    """Base exception class for JSON-LD messaging."""


class BadJWSHeaderError(BaseJSONLDMessagingError):
    """Exception indicating invalid JWS header."""


class DroppedAttributeError(BaseJSONLDMessagingError):
    """Exception used to track that an attribute was removed."""


class MissingVerificationMethodError(BaseJSONLDMessagingError):
    """Exception indicating missing verification method from signature options."""
