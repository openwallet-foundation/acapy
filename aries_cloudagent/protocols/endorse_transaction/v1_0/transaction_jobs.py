"""Class to manage jobs in Connection Record."""

from enum import Enum


class TransactionJob(Enum):
    """Represents jobs in Connection Record."""

    TRANSACTION_AUTHOR = (1,)
    TRANSACTION_ENDORSER = (2,)
