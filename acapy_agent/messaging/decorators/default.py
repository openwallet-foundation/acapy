"""Default decorator set implementation."""

from typing import Optional

from .base import BaseDecoratorSet
from .localization_decorator import LocalizationDecorator
from .service_decorator import ServiceDecorator
from .signature_decorator import SignatureDecorator
from .thread_decorator import ThreadDecorator
from .timing_decorator import TimingDecorator
from .trace_decorator import TraceDecorator
from .transport_decorator import TransportDecorator

DEFAULT_MODELS = {
    "l10n": LocalizationDecorator,
    "sig": SignatureDecorator,
    "thread": ThreadDecorator,
    "trace": TraceDecorator,
    "timing": TimingDecorator,
    "transport": TransportDecorator,
    "service": ServiceDecorator,
}


class DecoratorSet(BaseDecoratorSet):
    """Default decorator set implementation."""

    def __init__(self, models: Optional[dict] = None):
        """Initialize the decorator set."""
        super().__init__(DEFAULT_MODELS if models is None else models)
