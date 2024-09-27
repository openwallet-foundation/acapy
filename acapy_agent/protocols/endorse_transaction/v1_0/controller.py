"""Protocol controller for endorse transaction."""

from typing import Sequence

ENDORSE_TRANSACTION = "aries.transaction.endorse"
REFUSE_TRANSACTION = "aries.transaction.refuse"
WRITE_TRANSACTION = "aries.transaction.ledger.write"
WRITE_TRANSACTION = "aries.transaction.ledger.write"
WRITE_DID_TRANSACTION = "aries.transaction.ledger.write_did"
REGISTER_PUBLIC_DID = "aries.transaction.register_public_did"


class Controller:
    """Endorse transaction protocol controller."""

    def __init__(self, protocol: str):
        """Initialize the controller."""

    def determine_goal_codes(self) -> Sequence[str]:
        """Return defined goal_codes."""
        return [
            ENDORSE_TRANSACTION,
            REFUSE_TRANSACTION,
            WRITE_TRANSACTION,
            WRITE_DID_TRANSACTION,
            REGISTER_PUBLIC_DID,
        ]
