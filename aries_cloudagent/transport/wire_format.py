"""Abstract wire format classes."""

import json
import logging

from abc import abstractmethod
from typing import List, Sequence, Tuple, Union

from ..core.profile import ProfileSession
from ..messaging.util import time_now

from .inbound.receipt import MessageReceipt
from .error import WireFormatParseError

LOGGER = logging.getLogger(__name__)

DIDCOMM_V0_MIME_TYPE = "application/ssi-agent-wire"
DIDCOMM_V1_MIME_TYPE = "application/didcomm-envelope-enc"


class BaseWireFormat:
    """Abstract messaging wire format."""

    def __init__(self):
        """Initialize the base wire format instance."""

    @abstractmethod
    async def parse_message(
        self,
        session: ProfileSession,
        message_body: Union[str, bytes],
    ) -> Tuple[dict, MessageReceipt]:
        """
        Deserialize an incoming message and further populate the request context.

        Args:
            session: The profile session for providing wallet access
            message_body: The body of the message

        Returns:
            A tuple of the parsed message and a message receipt instance

        Raises:
            WireFormatParseError: If the message can't be parsed

        """

    @abstractmethod
    async def encode_message(
        self,
        session: ProfileSession,
        message_json: Union[str, bytes],
        recipient_keys: Sequence[str],
        routing_keys: Sequence[str],
        sender_key: str,
    ) -> Union[str, bytes]:
        """
        Encode an outgoing message for transport.

        Args:
            session: The profile session for providing wallet access
            message_json: The message body to serialize
            recipient_keys: A sequence of recipient verkeys
            routing_keys: A sequence of routing verkeys
            sender_key: The verification key of the sending agent

        Returns:
            The encoded message

        Raises:
            MessageEncodeError: If the message could not be encoded

        """

    @abstractmethod
    def get_recipient_keys(self, message_body: Union[str, bytes]) -> List[str]:
        """
        Get all recipient keys from a wire message.

        Args:
            message_body: The body of the message

        Returns:
            List of recipient keys from the message body

        Raises:
            RecipientKeysError: If the recipient keys could not be extracted

        """


class JsonWireFormat(BaseWireFormat):
    """Unencrypted wire format."""

    @abstractmethod
    async def parse_message(
        self,
        session: ProfileSession,
        message_body: Union[str, bytes],
    ) -> Tuple[dict, MessageReceipt]:
        """
        Deserialize an incoming message and further populate the request context.

        Args:
            session: The profile session for providing wallet access
            message_body: The body of the message

        Returns:
            A tuple of the parsed message and a message receipt instance

        Raises:
            WireFormatParseError: If the JSON parsing failed

        """
        receipt = MessageReceipt()
        receipt.in_time = time_now()
        receipt.raw_message = message_body

        message_dict = None
        message_json = message_body

        if not message_json:
            raise WireFormatParseError("Message body is empty")

        try:
            message_dict = json.loads(message_json)
        except ValueError:
            raise WireFormatParseError("Message JSON parsing failed")
        if not isinstance(message_dict, dict):
            raise WireFormatParseError("Message JSON result is not an object")

        # parse thread ID
        thread_dec = message_dict.get("~thread")
        receipt.thread_id = (
            thread_dec and thread_dec.get("thid") or message_dict.get("@id")
        )
        receipt.parent_thread_id = thread_dec.get("pthid") if thread_dec else None

        # handle transport decorator
        transport_dec = message_dict.get("~transport")
        if transport_dec:
            receipt.direct_response_mode = transport_dec.get("return_route")

        LOGGER.debug(f"Expanded message: {message_dict}")

        return message_dict, receipt

    @abstractmethod
    async def encode_message(
        self,
        session: ProfileSession,
        message_json: Union[str, bytes],
        recipient_keys: Sequence[str],
        routing_keys: Sequence[str],
        sender_key: str,
    ) -> Union[str, bytes]:
        """
        Encode an outgoing message for transport.

        Args:
            session: The profile session for providing wallet access
            message_json: The message body to serialize
            recipient_keys: A sequence of recipient verkeys
            routing_keys: A sequence of routing verkeys
            sender_key: The verification key of the sending agent

        Returns:
            The encoded message

        Raises:
            MessageEncodeError: If the message could not be encoded

        """
        return message_json

    def get_recipient_keys(self, message_body: Union[str, bytes]) -> List[str]:
        """
        Get all recipient keys from a wire message.

        Args:
            message_body: The body of the message

        Returns:
            List of recipient keys from the message body

        Raises:
            RecipientKeysError: If the recipient keys could not be extracted

        """

        # JSON message cannot contain recipient keys
        return []
