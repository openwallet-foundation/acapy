"""Common exception classes."""


class BaseError(Exception):
    """Generic exception class which other exceptions should inherit from."""


class StartupError(BaseError):
    """Error raised when there is a problem starting the conductor."""
