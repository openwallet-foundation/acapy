"""Default decorator set implementation."""

from .base import BaseDecoratorSet

from .localization_decorator import LocalizationDecorator
from .signature_decorator import SignatureDecorator
from .thread_decorator import ThreadDecorator
from .timing_decorator import TimingDecorator
from .transport_decorator import TransportDecorator

DEFAULT_MODELS = {
    "l10n": LocalizationDecorator,
    "sig": SignatureDecorator,
    "thread": ThreadDecorator,
    "timing": TimingDecorator,
    "transport": TransportDecorator,
}


class DecoratorSet(BaseDecoratorSet):
    """Default decorator set implementation."""

    def __init__(self, models: dict = None):
        """Initialize the decorator set."""
        super().__init__(DEFAULT_MODELS if models is None else models)
