"""Role determiner for the action menu message family."""

from typing import Sequence

from ...config.injection_context import InjectionContext

from .base_service import BaseMenuService
from .message_types import MESSAGE_FAMILY


async def role_determiner(context: InjectionContext, protocols: Sequence[str]) -> dict:
    """Determine what action menu roles are defined."""

    if MESSAGE_FAMILY not in protocols:
        return

    service = await context.inject(BaseMenuService, required=False)
    if service:
        return {MESSAGE_FAMILY: ["provider"]}
