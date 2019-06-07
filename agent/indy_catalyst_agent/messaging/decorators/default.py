"""Default decorator set implementation."""

from .base import BaseDecoratorSet

from .localization_decorator import LocalizationDecorator
from .thread_decorator import ThreadDecorator
from .timing_decorator import TimingDecorator
from .transport_decorator import TransportDecorator

DEFAULT_MODELS = {
    "l10n": LocalizationDecorator,
    "thread": ThreadDecorator,
    "timing": TimingDecorator,
    "transport": TransportDecorator,
}


class DecoratorSet(BaseDecoratorSet):
    """Default decorator set implementation."""

    def __init__(self):
        """Initialize the decorator set."""
        super().__init__(DEFAULT_MODELS)
