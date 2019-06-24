"""Common exception classes."""


class BaseError(Exception):
    """Generic exception class which other exceptions should inherit from."""

    error_code = None

    def __init__(self, *args, error_code: str = None, **kwargs):
        """Initialize a BaseError instance."""
        super().__init__(*args, **kwargs)
        if error_code:
            self.error_code = error_code


class StartupError(BaseError):
    """Error raised when there is a problem starting the conductor."""
