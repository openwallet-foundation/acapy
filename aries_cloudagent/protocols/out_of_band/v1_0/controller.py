"""Protocol controller for out-of-band."""

from typing import Sequence


class Controller:
    """Out-of-band protocol controller."""

    def __init__(self, protocol: str):
        """Initialize the controller."""

    def determine_goal_codes(self) -> Sequence[str]:
        """Return defined goal_codes."""
        return []
