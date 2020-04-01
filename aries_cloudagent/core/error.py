"""Common exception classes."""


class BaseError(Exception):
    """Generic exception class which other exceptions should inherit from."""

    error_code = None

    def __init__(self, *args, error_code: str = None, **kwargs):
        """Initialize a BaseError instance."""
        super().__init__(*args, **kwargs)
        if error_code:
            self.error_code = error_code

    @property
    def message(self) -> str:
        """Accessor for the error message."""
        return self.args and self.args[0]


class StartupError(BaseError):
    """Error raised when there is a problem starting the conductor."""


class ProtocolDefinitionValidationError(BaseError):
    """Error raised when there is a problem validating a protocol definition."""


class ProtocolMinorVersionNotSupported(BaseError):
    """
    Minimum minor version protocol error.

    Error raised when protocol support exists
    but minimum minor version is higher than in @type parameter.
    """
