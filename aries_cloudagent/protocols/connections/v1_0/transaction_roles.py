"""Class to manage roles in Connection Record."""

from enum import Enum


class TransactionRole(Enum):
    """Represents roles in Connection Record."""

    TRANSACTION_AUTHOR = (1,)
    TRANSACTION_ENDORSER = (2,)
