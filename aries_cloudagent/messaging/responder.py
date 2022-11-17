"""
A message responder.

The responder is provided to message handlers to enable them to send a new message
in response to the message being handled.
"""

from abc import ABC, abstractmethod
import json
from typing import Sequence, Union

from ..connections.models.connection_target import ConnectionTarget
from ..core.error import BaseError
from ..transport.outbound.message import OutboundMessage

from .base_message import BaseMessage
from ..transport.outbound.status import OutboundSendStatus


class ResponderError(BaseError):
    """Responder error."""


class BaseResponder(ABC):
    """Interface for message handlers to send responses."""

    def __init__(
        self,
        *,
        connection_id: str = None,
        reply_session_id: str = None,
        reply_to_verkey: str = None,
    ):
        """Initialize a base responder."""
        self.connection_id = connection_id
        self.reply_session_id = reply_session_id
        self.reply_to_verkey = reply_to_verkey

    async def create_outbound(
        self,
        message: Union[BaseMessage, str, bytes],
        *,
        connection_id: str = None,
        reply_session_id: str = None,
        reply_thread_id: str = None,
        reply_to_verkey: str = None,
        reply_from_verkey: str = None,
        target: ConnectionTarget = None,
        target_list: Sequence[ConnectionTarget] = None,
        to_session_only: bool = False,
    ) -> OutboundMessage:
        """Create an OutboundMessage from a message payload."""
        if isinstance(message, BaseMessage):
            # TODO DIDComm version selection
            serialized = message.serialize()
            # TODO serialized format selection?
            payload = json.dumps(serialized)
            enc_payload = None
            if not reply_thread_id:
                reply_thread_id = message._thread_id
        else:
            payload = None
            enc_payload = message
        return OutboundMessage(
            connection_id=connection_id,
            enc_payload=enc_payload,
            payload=payload,
            reply_session_id=reply_session_id,
            reply_thread_id=reply_thread_id,
            reply_to_verkey=reply_to_verkey,
            reply_from_verkey=reply_from_verkey,
            target=target,
            target_list=target_list,
            to_session_only=to_session_only,
        )

    async def send(
        self, message: Union[BaseMessage, str, bytes], **kwargs
    ) -> OutboundSendStatus:
        """Convert a message to an OutboundMessage and send it."""
        outbound = await self.create_outbound(message, **kwargs)
        return await self.send_outbound(outbound)

    async def send_reply(
        self,
        message: Union[BaseMessage, str, bytes],
        *,
        connection_id: str = None,
        target: ConnectionTarget = None,
        target_list: Sequence[ConnectionTarget] = None,
    ) -> OutboundSendStatus:
        """
        Send a reply to an incoming message.

        Args:
            message: the `BaseMessage`, or pre-packed str or bytes to reply with
            connection_id: optionally override the target connection ID
            target: optionally specify a `ConnectionTarget` to send to

        Raises:
            ResponderError: If there is no active connection

        """
        outbound = await self.create_outbound(
            message,
            connection_id=connection_id or self.connection_id,
            reply_session_id=self.reply_session_id,
            reply_to_verkey=self.reply_to_verkey,
            target=target,
            target_list=target_list,
        )
        return await self.send_outbound(outbound)

    @abstractmethod
    async def send_outbound(self, message: OutboundMessage) -> OutboundSendStatus:
        """
        Send an outbound message.

        Args:
            message: The `OutboundMessage` to be sent
        """

    @abstractmethod
    async def send_webhook(self, topic: str, payload: dict):
        """
        Dispatch a webhook. DEPRECATED: use the event bus instead.

        Args:
            topic: the webhook topic identifier
            payload: the webhook payload value
        """


class MockResponder(BaseResponder):
    """Mock responder implementation for use by tests."""

    def __init__(self):
        """Initialize the mock responder."""
        self.messages = []

    async def send(
        self, message: Union[BaseMessage, str, bytes], **kwargs
    ) -> OutboundSendStatus:
        """Convert a message to an OutboundMessage and send it."""
        self.messages.append((message, kwargs))
        return OutboundSendStatus.QUEUED_FOR_DELIVERY

    async def send_reply(
        self, message: Union[BaseMessage, str, bytes], **kwargs
    ) -> OutboundSendStatus:
        """Send a reply to an incoming message."""
        self.messages.append((message, kwargs))
        return OutboundSendStatus.QUEUED_FOR_DELIVERY

    async def send_outbound(self, message: OutboundMessage) -> OutboundSendStatus:
        """Send an outbound message."""
        self.messages.append((message, None))
        return OutboundSendStatus.QUEUED_FOR_DELIVERY

    async def send_webhook(self, topic: str, payload: dict):
        """Send an outbound message."""
        raise Exception(
            "responder.send_webhook is deprecated; please use the event bus instead."
        )
