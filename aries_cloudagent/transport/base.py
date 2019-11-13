"""Abstract wire format classes."""

from abc import abstractmethod

from typing import Sequence, Tuple, Union

from ..config.injection_context import InjectionContext
from .inbound.receipt import MessageReceipt


class BaseWireFormat:
    """Abstract messaging wire format."""

    def __init__(self):
        """Initialize the base wire format instance."""

    @abstractmethod
    async def parse_message(
        self, context: InjectionContext, message_body: Union[str, bytes],
    ) -> Tuple[dict, MessageReceipt]:
        """
        Deserialize an incoming message and further populate the request context.

        Args:
            context: The injection context for settings and services
            message_body: The body of the message

        Returns:
            A tuple of the parsed message and a message receipt instance

        Raises:
            MessageParseError: If the JSON parsing failed
            MessageParseError: If a wallet is required but can't be located

        """

    @abstractmethod
    async def encode_message(
        self,
        context: InjectionContext,
        message_json: Union[str, bytes],
        recipient_keys: Sequence[str],
        routing_keys: Sequence[str],
        sender_key: str,
    ) -> Union[str, bytes]:
        """
        Encode an outgoing message for transport.

        Args:
            context: The injection context for settings and services
            message_json: The message body to serialize
            recipient_keys: A sequence of recipient verkeys
            routing_keys: A sequence of routing verkeys
            sender_key: The verification key of the sending agent

        Returns:
            The encoded message

        Raises:
            MessageEncodeError: If the message could not be encoded

        """
