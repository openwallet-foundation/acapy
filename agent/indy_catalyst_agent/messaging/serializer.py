"""Standard message serializer classes."""

import json
import logging
from typing import Tuple, Union

from ..config.base import InjectorError
from ..config.injection_context import InjectionContext
from ..messaging.connections.models.connection_target import ConnectionTarget
from ..messaging.routing.messages.forward import Forward
from ..wallet.base import BaseWallet
from ..wallet.error import WalletError

from .agent_message import AgentMessage
from .message_delivery import MessageDelivery
from .error import MessageParseError
from .util import time_now

LOGGER = logging.getLogger(__name__)


class MessageSerializer:
    """Standard DIDComm message parser and serializer."""

    async def parse_message(
        self,
        context: InjectionContext,
        message_body: Union[str, bytes],
        transport_type: str,
    ) -> Tuple[dict, MessageDelivery]:
        """
        Deserialize an incoming message and further populate the request context.

        Args:
            context: The injection context for settings and services
            message_body: The body of the message
            transport_type: The transport the message was received on

        Returns:
            A message delivery object with details on the parsed message

        Raises:
            MessageParseError: If the JSON parsing failed
            MessageParseError: If a wallet is required but can't be located

        """

        delivery = MessageDelivery()
        delivery.in_time = time_now()
        delivery.raw_message = message_body
        delivery.transport_type = transport_type

        message_dict = None
        message_json = message_body

        try:
            message_dict = json.loads(message_json)
        except ValueError:
            raise MessageParseError("Message JSON parsing failed")
        if not isinstance(message_dict, dict):
            raise MessageParseError("Message JSON parsing failed")

        if "@type" not in message_dict:
            try:
                wallet: BaseWallet = await context.inject(BaseWallet)
            except InjectorError:
                raise MessageParseError("Wallet not defined in request context")

            try:
                unpacked = await wallet.unpack_message(message_body)
                message_json, delivery.sender_verkey, delivery.recipient_verkey = (
                    unpacked
                )
            except WalletError:
                LOGGER.debug("Message unpack failed, falling back to JSON")
            else:
                delivery.raw_message = message_json
                try:
                    message_dict = json.loads(message_json)
                except ValueError:
                    raise MessageParseError("Message JSON parsing failed")

        LOGGER.debug(f"Expanded message: {message_dict}")

        # handle transport decorator
        transport_dec = message_dict.get("~transport")
        if transport_dec:
            delivery.direct_response_requested = transport_dec.get("return_route")

        return delivery, message_dict

    def extract_message_type(self, parsed_msg: dict) -> str:
        """
        Extract the message type identifier from a parsed message.

        Raises:
            MessageParseError: If the message doesn't specify a type

        """

        msg_type = parsed_msg.get("@type")
        if not msg_type:
            raise MessageParseError("Message does not contain '@type' parameter")
        return msg_type

    async def compact_message(
        self,
        context: InjectionContext,
        message: Union[AgentMessage, str, bytes],
        target: ConnectionTarget,
    ) -> Union[str, bytes]:
        """
        Serialize an outgoing message for transport.

        Args:
            context: The injection context for settings and services
            message: The `AgentMessage` to compact, or a pre-packed string or bytes
            target: The `ConnectionTarget` you are compacting for

        Returns:
            The serialized message

        """

        wallet: BaseWallet = await context.inject(BaseWallet)

        if isinstance(message, AgentMessage):
            message_json = message.to_json()
            if target and target.sender_key and target.recipient_keys:
                message = await wallet.pack_message(
                    message_json, target.recipient_keys, target.sender_key
                )
                if target.routing_keys:
                    recip_keys = target.recipient_keys
                    for router_key in target.routing_keys:
                        fwd_msg = Forward(to=recip_keys[0], msg=message)
                        # Forwards are anon packed
                        recip_keys = [router_key]
                        message = await wallet.pack_message(
                            fwd_msg.to_json(), recip_keys
                        )
            else:
                message = message_json
        return message
