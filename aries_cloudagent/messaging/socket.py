"""Duplex connection handling classes."""

import asyncio
from typing import Coroutine, Sequence
import uuid

from .message_delivery import MessageDelivery
from .outbound_message import OutboundMessage


class SocketInfo:
    """Track an open transport connection for direct routing of outbound messages."""

    REPLY_MODE_ALL = "all"
    REPLY_MODE_NONE = "none"
    REPLY_MODE_THREAD = "thread"

    def __init__(
        self,
        *,
        connection_id: str = None,
        handler: Coroutine = None,
        reply_mode: str = None,
        reply_thread_ids: Sequence[str] = None,
        reply_verkeys: Sequence[str] = None,
        single_response: asyncio.Future = None,
        socket_id: str = None,
    ):
        """Initialize the socket info."""
        self._closed = False
        self.connection_id = connection_id
        self.handler = handler
        self.reply_thread_ids = set(reply_thread_ids) if reply_thread_ids else set()
        self.reply_verkeys = set(reply_verkeys) if reply_verkeys else set()
        self.single_response = single_response
        self.socket_id = socket_id or str(uuid.uuid4())
        # calls setter
        self._reply_mode = None
        self.reply_mode = reply_mode

    @property
    def closed(self) -> bool:
        """Accessor for the socket closed state."""
        if self._closed:
            return True
        if self.single_response and self.single_response.done():
            self._closed = True
            return True
        return False

    @closed.setter
    def closed(self, flag: bool):
        """Setter for the socket closed state."""
        self._closed = flag

    @property
    def reply_mode(self) -> str:
        """Accessor for the socket reply mode."""
        return self._reply_mode

    @reply_mode.setter
    def reply_mode(self, mode: str):
        """Setter for the socket reply mode."""
        if mode not in (self.REPLY_MODE_ALL, self.REPLY_MODE_THREAD):
            mode = None
            # reset the tracked thread IDs when the mode is changed to none
            self.reply_thread_ids = set()
        self._reply_mode = mode

    def add_reply_thread_id(self, thid: str):
        """Add a thread ID to the set of potential reply targets."""
        if thid:
            self.reply_thread_ids.add(thid)

    def add_reply_verkey(self, verkey: str):
        """Add a verkey to the set of potential reply targets."""
        if verkey:
            self.reply_verkeys.add(verkey)

    def process_incoming(self, parsed_msg: dict, delivery: MessageDelivery):
        """Process an incoming message and update the socket metadata as necessary.

        Args:
            parsed_msg: The unserialized message body
            delivery: The message delivery metadata
        """
        mode = self.reply_mode = delivery.direct_response_requested
        self.add_reply_verkey(delivery.sender_verkey)
        if mode == self.REPLY_MODE_THREAD:
            self.add_reply_thread_id(delivery.thread_id)
        delivery.direct_response = bool(mode)
        if delivery.connection_id:
            self.connection_id = delivery.connection_id

    def dispatch_complete(self):
        """Indicate that a message handler has completed."""
        if not self.closed and self.single_response:
            self.single_response.cancel()

    def select_outgoing(self, message: OutboundMessage) -> bool:
        """Determine if an outbound message should be sent to this socket.

        Args:
            message: The outbound message to be checked
        """
        mode = self.reply_mode
        if not self.closed:
            if (
                mode == self.REPLY_MODE_ALL
                and message.reply_socket_id == self.socket_id
            ):
                return True
            if (
                mode == self.REPLY_MODE_ALL
                and message.reply_to_verkey
                and message.reply_to_verkey in self.reply_verkeys
            ):
                return True
            if (
                mode == self.REPLY_MODE_ALL
                and message.target
                and message.target.recipient_keys
                and any(True for k in message.target.recipient_keys
                        if k in self.reply_verkeys)
            ):
                return True
            if (
                mode == self.REPLY_MODE_THREAD
                and message.reply_thread_id
                and message.reply_thread_id in self.reply_thread_ids
            ):
                return True
        return False

    async def send(self, message: OutboundMessage):
        """."""
        if self.single_response:
            self.single_response.set_result(message.payload)
        elif self.handler:
            await self.handler(message.payload)


class SocketRef:
    """A reference to a registered duplex connection."""

    def __init__(self, socket_id: str, close: Coroutine):
        """Initialize the socket reference."""
        self.close = close
        self.socket_id = socket_id
