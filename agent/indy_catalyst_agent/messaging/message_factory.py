"""Handle identification of message types and instantiation of message classes."""

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
        Desererialize a message dict into a relevant message instance.

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
