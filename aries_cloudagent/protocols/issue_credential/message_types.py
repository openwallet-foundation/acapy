"""All issue_credential message types."""

from .v1_0.message_types import MESSAGE_TYPES as V10_MESSAGE_TYPES
from .v1_1.message_types import MESSAGE_TYPES as V11_MESSAGE_TYPES

MESSAGE_TYPES = {
    **V10_MESSAGE_TYPES,
    **V11_MESSAGE_TYPES
}
__all__ = ("MESSAGE_TYPES",)
