"""Class to manage roles in Connection Record."""

from enum import Enum


class Role(Enum):
    """Represents roles in Connection Record."""

    AUTHOR = (1,)
    ENDORSER = (2,)
