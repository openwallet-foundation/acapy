"""
Handle identification of message types and instantiation of message classes
"""

from ..classloader import ClassLoader
from ..error import BaseError

from .agent_message import AgentMessage


class MessageParseError(BaseError):
    """Message parse error."""

    pass


class MessageFactory:
    """
    Message factory for deserializing message json and obtaining relevant
    message class
    """

    def __init__(self):
        self._typemap = {}

    def register_message_types(self, *types):
        """
        Add new supported message types.

        :param *types:

        """
        for typeset in types:
            self._typemap.update(typeset)

    def resolve_message_class(self, message_type: str) -> type:
        """
        Given a dict describing a message, this method
        returns the corresponding registered message class.

        :param message_type: str:
        """
        msg_cls = self._typemap.get(message_type)
        if isinstance(msg_cls, str):
            msg_cls = ClassLoader.load_class(msg_cls)
        return msg_cls

    def make_message(self, serialized_msg: dict) -> AgentMessage:
        """
        Given a dict describing a message, this method
        returns an instance of the related message class.

        :param serialized_msg: dict:

        """

        msg_type = serialized_msg.get("@type")
        if not msg_type:
            raise MessageParseError("Message does not contain '@type' parameter")

        msg_cls = self.resolve_message_class(msg_type)
        if not msg_cls:
            raise MessageParseError(f"Unrecognized message type {msg_type}")

        instance = msg_cls.deserialize(serialized_msg)
        return instance

    def __repr__(self) -> str:
        return "<{}>".format(self.__class__.__name__)
