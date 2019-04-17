"""Handle identification of message types and instantiation of message classes."""

from typing import Sequence

from ..classloader import ClassLoader
from ..error import BaseError

from .agent_message import AgentMessage
from ..models.base import BaseModelError


class MessageParseError(BaseError):
    """Message parse error."""


class MessageFactory:
    """Message factory for deserializing messages."""

    def __init__(self):
        """Initialize a MessageFactory instance."""
        self._typemap = {}

    @property
    def protocols(self) -> Sequence[str]:
        """Accessor for a list of all message protocols."""
        prots = {}
        for message_type in self._typemap.keys():
            pos = message_type.rfind("/")
            if pos:
                family = message_type[:pos]
                prots[family] = True
        return tuple(prots.keys())

    @property
    def message_types(self) -> Sequence[str]:
        """Accessor for a list of all message types."""
        return tuple(self._typemap.keys())

    def protocols_matching_query(self, query: str) -> Sequence[str]:
        """Return a list of message protocols matching a query string."""
        all_types = self.protocols
        result = None

        if query == "*":
            result = all_types
        elif query:
            if query.endswith("*"):
                match = query[:-1]
                result = tuple(k for k in all_types if k.startswith(match))
            elif query in all_types:
                result = (query,)
        return result or ()

    def register_message_types(self, *types):
        """
        Add new supported message types.

        Args:
            *types: Message types to register

        """
        for typeset in types:
            self._typemap.update(typeset)

    def resolve_message_class(self, message_type: str) -> type:
        """
        Resolve a message_type to a message class.

        Given a dict describing a message, this method
        returns the corresponding registered message class.

        Args:
            message_type: Message type to resolve

        Returns:
            The resolved message class

        """
        msg_cls = self._typemap.get(message_type)
        if isinstance(msg_cls, str):
            msg_cls = ClassLoader.load_class(msg_cls)
        return msg_cls

    def make_message(self, serialized_msg: dict) -> AgentMessage:
        """
        Deserialize a message dict into a relevant message instance.

        Given a dict describing a message, this method
        returns an instance of the related message class.

        Args:
            serialized_msg: The serialized message

        Returns:
            An instance of the corresponding message class for this message

        Raises:
            MessageParseError: If the message doesn't specify @type
            MessageParseError: If there is no message class registered to handle
                the given type

        """

        msg_type = serialized_msg.get("@type")
        if not msg_type:
            raise MessageParseError("Message does not contain '@type' parameter")

        msg_cls = self.resolve_message_class(msg_type)
        if not msg_cls:
            raise MessageParseError(f"Unrecognized message type {msg_type}")

        try:
            instance = msg_cls.deserialize(serialized_msg)
        except BaseModelError as e:
            raise MessageParseError(f"Error deserializing message: {e}") from e

        return instance

    def __repr__(self) -> str:
        """Return a string representation for this class."""
        return "<{}>".format(self.__class__.__name__)
