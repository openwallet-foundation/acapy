"""Base holder class."""

from abc import ABC


class BaseHolder(ABC):
    """Base class for holder."""

    def __repr__(self) -> str:
        """
        Return a human readable representation of this class.

        Returns:
            A human readable string for this class

        """
        return "<{}>".format(self.__class__.__name__)
