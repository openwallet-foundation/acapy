"""Base message."""

from abc import ABC, abstractclassmethod, abstractmethod, abstractproperty
from enum import Enum, auto
from typing import Optional, Type, TYPE_CHECKING

if TYPE_CHECKING:
    from .base_handler import BaseHandler


class DIDCommVersion(Enum):
    """Serialized message formats."""

    v1 = auto()
    v2 = auto()


class BaseMessage(ABC):
    """Abstract base class for messages.

    This formally defines a "minimum viable message" and provides an
    unopinionated class for plugins to extend in whatever way makes sense in
    the context of the plugin.
    """

    @abstractproperty
    def _type(self) -> str:
        """Return message type."""

    @abstractproperty
    def _id(self) -> str:
        """Return message id."""

    @abstractproperty
    def _thread_id(self) -> Optional[str]:
        """Return message thread id."""

    @abstractmethod
    def serialize(self, msg_format: DIDCommVersion = DIDCommVersion.v1) -> dict:
        """Return serialized message in format specified."""

    @abstractclassmethod
    def deserialize(cls, value: dict, msg_format: DIDCommVersion = DIDCommVersion.v1):
        """Return message object deserialized from value in format specified."""

    @abstractproperty
    def Handler(self) -> Type["BaseHandler"]:
        """Return reference to handler class."""
