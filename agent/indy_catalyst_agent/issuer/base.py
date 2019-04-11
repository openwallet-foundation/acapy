"""Ledger issuer class."""

from abc import ABC


class BaseIssuer(ABC):
    """Base class for issuer."""

    def __repr__(self) -> str:
        """
        Return a human readable representation of this class.

        Returns:
            A human readable string for this class

        """
        return "<{}>".format(self.__class__.__name__)
