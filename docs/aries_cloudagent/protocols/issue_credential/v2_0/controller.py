"""Protocol controller for issue credential v2_0."""

from typing import Sequence

PARTICIPATE_VC_INTERACTION = "aries.vc"
ISSUE_VC = "aries.vc.issue"


class Controller:
    """Issue credential v2_0 protocol controller."""

    def __init__(self, protocol: str):
        """Initialize the controller."""

    def determine_goal_codes(self) -> Sequence[str]:
        """Return defined goal_codes."""
        return [PARTICIPATE_VC_INTERACTION, ISSUE_VC]
