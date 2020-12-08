"""Protocol controller for the action menu message family."""

from typing import Sequence

from ....config.injection_context import InjectionContext

from .base_service import BaseMenuService


class Controller:
    """Action menu protocol controller."""

    def __init__(self, protocol: str):
        """Initialize the controller."""

    async def determine_roles(self, context: InjectionContext) -> Sequence[str]:
        """Determine what action menu roles are defined."""

        service = context.inject(BaseMenuService, required=False)
        if service:
            return ["provider"]
