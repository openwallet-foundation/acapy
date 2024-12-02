"""Custom logging filters for aca-py agent."""

import logging
from contextvars import ContextVar

context_wallet_id: ContextVar[str] = ContextVar("context_wallet_id")


class ContextFilter(logging.Filter):
    """Custom logging Filter to adapt logs with contextual wallet_id."""

    def __init__(self):
        """Initialize an instance of Custom logging.Filter."""
        super().__init__()

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter LogRecords and add wallet_id to them."""
        try:
            wallet_id = context_wallet_id.get()
            record.wallet_id = wallet_id
            return True
        except LookupError:
            record.wallet_id = None
            return True
