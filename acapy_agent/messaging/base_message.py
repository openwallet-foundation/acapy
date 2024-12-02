"""Base message."""

from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import TYPE_CHECKING, Optional, Type

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

    @property
    @abstractmethod
    def _type(self) -> str:
        """Return message type."""

    @property
    @abstractmethod
    def _id(self) -> str:
        """Return message id."""

    @property
    @abstractmethod
    def _thread_id(self) -> Optional[str]:
        """Return message thread id."""

    @abstractmethod
    def serialize(self, msg_format: DIDCommVersion = DIDCommVersion.v1) -> dict:
        """Return serialized message in format specified."""

    @classmethod
    @abstractmethod
    def deserialize(cls, value: dict, msg_format: DIDCommVersion = DIDCommVersion.v1):
        """Return message object deserialized from value in format specified."""

    @property
    @abstractmethod
    def Handler(self) -> Type["BaseHandler"]:
        """Return reference to handler class."""
