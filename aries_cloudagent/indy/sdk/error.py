"""Indy error handling."""

from typing import Type

from indy.error import IndyError

from ...core.error import BaseError


class IndyErrorHandler:
    """Trap IndyError and raise an appropriate LedgerError instead."""

    def __init__(self, message: str = None, error_cls: Type[BaseError] = BaseError):
        """Init the context manager."""
        self.error_cls = error_cls
        self.message = message

    def __enter__(self):
        """Enter the context manager."""
        return self

    def __exit__(self, err_type, err_value, err_traceback):
        """Exit the context manager."""
        if isinstance(err_value, IndyError):
            raise IndyErrorHandler.wrap_error(
                err_value, self.message, self.error_cls
            ) from err_value

    @classmethod
    def wrap_error(
        cls,
        err_value: IndyError,
        message: str = None,
        error_cls: Type[BaseError] = BaseError,
    ) -> BaseError:
        """Create an instance of BaseError from an IndyError."""
        err_msg = message or "Exception while performing indy operation"
        indy_message = hasattr(err_value, "message") and err_value.message
        if indy_message:
            err_msg += f": {indy_message}"
        err = error_cls(err_msg)
        err.__traceback__ = err_value.__traceback__
        return err
