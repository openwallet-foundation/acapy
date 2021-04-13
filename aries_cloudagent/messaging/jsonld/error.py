"""JSON-LD messaging Exceptions."""

from ...core.error import BaseError


class BaseJSONLDMessagingError(BaseError):
    """Base exception class for JSON-LD messaging."""


class BadJWSHeaderError(BaseJSONLDMessagingError):
    """Invalid JWS header provided."""


class DroppedAttributeError(BaseJSONLDMessagingError):
    """Exception used to track that an attribute was removed."""


class MissingVerificationMethodError(BaseJSONLDMessagingError):
    """Exception indicating missing verification method from signature options."""


class SignatureTypeError(BaseJSONLDMessagingError):
    """Signature type error."""
