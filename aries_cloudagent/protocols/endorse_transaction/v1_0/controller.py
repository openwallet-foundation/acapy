"""Protocol controller for endorse transaction."""

from typing import Sequence

ENDORSE_TRANSACTION = "aries.transaction.endorse"
REFUSE_TRANSACTION = "aries.transaction.refuse"
WRITE_TRANSACTION = "aries.transaction.ledger.write"


class Controller:
    """Endorse transaction protocol controller."""

    def __init__(self, protocol: str):
        """Initialize the controller."""

    def determine_goal_codes(self) -> Sequence[str]:
        """Return defined goal_codes."""
        return [ENDORSE_TRANSACTION, REFUSE_TRANSACTION, WRITE_TRANSACTION]
