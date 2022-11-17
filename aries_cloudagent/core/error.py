"""Common exception classes."""

import re


class BaseError(Exception):
    """Generic exception class which other exceptions should inherit from."""

    def __init__(self, *args, error_code: str = None, **kwargs):
        """Initialize a BaseError instance."""
        super().__init__(*args, **kwargs)
        self.error_code = error_code if error_code else None

    @property
    def message(self) -> str:
        """Accessor for the error message."""
        return str(self.args[0]).strip() if self.args else ""

    @property
    def roll_up(self) -> str:
        """
        Accessor for nested error messages rolled into one line.

        For display: aiohttp.web errors truncate after newline.
        """

        def flatten(exc: Exception):
            return ".".join(
                (
                    re.sub(
                        r"\n\s*",
                        ". ",
                        (
                            str(exc.args[0]).strip()
                            if exc.args
                            else exc.__class__.__name__
                        ),
                    ).strip()
                ).rsplit(".", 1)
            )

        line = flatten(self)
        err = self
        while err.__cause__:
            err = err.__cause__
            line += ". {}".format(flatten(err))
        return f"{line.strip()}."


class ProfileError(BaseError):
    """Base error for profile operations."""


class ProfileDuplicateError(ProfileError):
    """Profile with the given name already exists."""


class ProfileNotFoundError(ProfileError):
    """Requested profile was not found."""


class ProfileSessionInactiveError(ProfileError):
    """Error raised when a profile session is not currently active."""


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
