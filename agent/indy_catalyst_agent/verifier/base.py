"""Base Verifier class."""

from abc import ABC


class BaseVerifier(ABC):
    """Base class for verifier."""

    def __repr__(self) -> str:
        """
        Return a human readable representation of this class.

        Returns:
            A human readable string for this class

        """
        return "<{}>".format(self.__class__.__name__)
