"""Protocol controller for present proof v1_0."""

from typing import Sequence

VERIFY_VC = "aries.vc.verify"


class Controller:
    """Present proof v1_0 protocol controller."""

    def __init__(self, protocol: str):
        """Initialize the controller."""

    def determine_goal_codes(self) -> Sequence[str]:
        """Return defined goal_codes."""
        return [VERIFY_VC]
