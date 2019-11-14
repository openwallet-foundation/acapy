"""Inbound connection handling classes."""

import asyncio
from typing import Callable, Sequence, Tuple, Union

from ...config.injection_context import InjectionContext

from ..base import BaseWireFormat
from ..error import WireFormatError
from ..outbound.message import OutboundMessage

from .message import InboundMessage


class InboundSession:
    """Track an open transport connection for direct routing of outbound messages."""

    REPLY_MODE_ALL = "all"
    REPLY_MODE_NONE = "none"
    REPLY_MODE_THREAD = "thread"

    def __init__(
        self,
        *,
        context: InjectionContext,
        inbound_handler: Callable,
        session_id: str,
        wire_format: BaseWireFormat,
        client_info: dict = None,
        close_handler: Callable = None,
        reply_mode: str = None,
        reply_thread_ids: Sequence[str] = None,
        reply_verkeys: Sequence[str] = None,
        transport_type: str = None,
    ):
        """Initialize the inbound session."""
        self._closed = False
        self.context = context
        self.client_info = client_info
        self.close_handler = close_handler
        self.inbound_handler = inbound_handler
        self.outbound_buffer: OutboundMessage = None
        self.outbound_event = asyncio.Event()
        self.reply_thread_ids = set(reply_thread_ids) if reply_thread_ids else set()
        self.reply_verkeys = set(reply_verkeys) if reply_verkeys else set()
        self._reply_mode = None
        self.reply_mode = reply_mode  # calls setter
        self.session_id = session_id
        self.transport_type = transport_type
        self.wire_format = wire_format

    @property
    def closed(self) -> bool:
        """Accessor for the session closed state."""
        return self._closed

    def close(self):
        """Setter for the session closed state."""
        self._closed = True
        self.outbound_event.set()  # end wait_response if blocked
        if self.close_handler:
            self.close_handler(self)

    @property
    def reply_mode(self) -> str:
        """Accessor for the session reply mode."""
        return self._reply_mode

    @reply_mode.setter
    def reply_mode(self, mode: str):
        """Setter for the session reply mode."""
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

    def process_inbound(self, message: InboundMessage):
        """
        Process an incoming message and update the session metadata as necessary.

        Args:
            message: The inbound message instance
        """
        receipt = message.receipt
        mode = self.reply_mode = receipt.direct_response_requested
        self.add_reply_verkey(receipt.sender_verkey)
        if mode == self.REPLY_MODE_THREAD:
            self.add_reply_thread_id(receipt.thread_id)

    async def receive(self, payload_enc: Union[str, bytes]) -> InboundMessage:
        payload, receipt = await self.wire_format.parse_message(
            self.context, payload_enc
        )
        message = InboundMessage(
            payload,
            receipt,
            session_id=self.session_id,
            transport_type=self.transport_type,
        )
        self.receive_inbound(message)
        return message

    def receive_inbound(self, message: InboundMessage):
        """Deliver the inbound message to the conductor."""
        self.process_inbound(message)
        self.inbound_handler(message)

    def select_outbound(self, message: OutboundMessage) -> bool:
        """Determine if an outbound message should be sent to this session.

        Args:
            message: The outbound message to be checked

        """
        if self.closed or not self.can_respond:
            return False

        mode = self.reply_mode
        if mode == self.REPLY_MODE_ALL:
            if (
                message.reply_session_id and message.reply_session_id == self.session_id
            ) or (
                message.reply_to_verkey
                and message.reply_to_verkey in self.reply_verkeys
            ):
                return True
        elif (
            mode == self.REPLY_MODE_THREAD
            and message.reply_thread_id
            and message.reply_thread_id in self.reply_thread_ids
            and message.reply_to_verkey
            and message.reply_to_verkey in self.reply_verkeys
        ):
            return True

        return False

    def accept_response(self, message: OutboundMessage) -> Tuple[bool, bool]:
        """
        Try to queue an outbound message if it applies to this session.

        Returns: a tuple of (message buffered, retry later)
        """
        if not self.select_outbound(message):
            return (False, False)
        if self.outbound_buffer:
            return (False, True)
        self.outbound_buffer = message
        self.outbound_event.set()
        return (True, False)

    def clear_outbound(self):
        """Called when the outbound buffered message has been delivered."""
        self.outbound_buffer = None
        self.outbound_event.clear()

    async def wait_response(self) -> OutboundMessage:
        """Wait for a response to be buffered and unpack it."""
        await self.outbound_event
        response = self.outbound_buffer
        if response and not response.enc_payload:
            if not response.payload:
                raise WireFormatError("Message has no payload to encode")
            if not response.target:
                raise WireFormatError("No target available for encoding message")

            target = response.target
            response.enc_payload = await self.wire_format.encode_message(
                self.context,
                response.payload,
                target.recipient_keys,
                None,
                target.sender_key,
            )

        return response

    def no_response(self, message: InboundMessage):
        # need to close the connection if nothing was queued for it
        # more complicated if the connection has received multiple messages
        self.outbound_event.set()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_value, exc_tb):
        """Async context manager entry."""
        self.close()
