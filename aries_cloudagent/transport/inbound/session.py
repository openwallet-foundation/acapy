"""Inbound connection handling classes."""

import asyncio
import logging
from typing import Callable, Sequence, Union

from ...admin.server import AdminResponder
from ...core.profile import Profile
from ...messaging.responder import BaseResponder
from ...multitenant.base import BaseMultitenantManager

from ..error import WireFormatError
from ..outbound.message import OutboundMessage
from ..wire_format import BaseWireFormat

from .message import InboundMessage
from .receipt import MessageReceipt

LOGGER = logging.getLogger(__name__)


class AcceptResult:
    """Represent the result of accept_response."""

    def __init__(self, accepted: bool, retry: bool = False):
        """Initialize the `AcceptResult` instance."""
        self.accepted = accepted
        self.retry = retry

    def __bool__(self) -> bool:
        """Check if the result is true."""
        return self.accepted


class InboundSession:
    """Track an open transport connection for direct routing of outbound messages."""

    def __init__(
        self,
        *,
        profile: Profile,
        inbound_handler: Callable,
        session_id: str,
        wire_format: BaseWireFormat,
        accept_undelivered: bool = False,
        can_respond: bool = False,
        client_info: dict = None,
        close_handler: Callable = None,
        reply_mode: str = None,
        reply_thread_ids: Sequence[str] = None,
        reply_verkeys: Sequence[str] = None,
        transport_type: str = None,
    ):
        """Initialize the inbound session."""
        self.profile = profile
        self.inbound_handler = inbound_handler
        self.session_id = session_id
        self.wire_format = wire_format

        self.accept_undelivered = accept_undelivered
        self.client_info = client_info
        self.close_handler = close_handler
        self.response_buffer: OutboundMessage = None
        self.response_event = asyncio.Event()
        self.transport_type = transport_type

        self._can_respond = can_respond
        self._closed = False
        self._reply_mode = None
        self._reply_verkeys = None
        self._reply_thread_ids = None

        # If multitenancy is enabled we need to relay the message by changing
        # the context/profile to the wallet associated with the message.
        # Only needs to happen for the first received message
        self._check_relay_context = profile.context.settings.get(
            "multitenant.enabled", False
        )

        # call setters
        self.reply_thread_ids = reply_thread_ids
        self.reply_verkeys = reply_verkeys
        self.reply_mode = reply_mode

    @property
    def can_respond(self) -> bool:
        """Accessor for the session can-respond state."""
        return self._can_respond and not self._closed

    @can_respond.setter
    def can_respond(self, can_respond: bool):
        """Setter for the session can-respond state."""
        self._can_respond = can_respond

    @property
    def closed(self) -> bool:
        """Accessor for the session closed state."""
        return self._closed

    def close(self):
        """Setter for the session closed state."""
        self._closed = True
        self.response_event.set()  # end wait_response if blocked
        if self.close_handler:
            self.close_handler(self)

    @property
    def reply_mode(self) -> str:
        """Accessor for the session reply mode."""
        return self._reply_mode

    @reply_mode.setter
    def reply_mode(self, mode: str):
        """Setter for the session reply mode."""
        if mode not in (
            MessageReceipt.REPLY_MODE_ALL,
            MessageReceipt.REPLY_MODE_THREAD,
        ):
            mode = None
        self._reply_mode = mode
        if not mode:
            # reset the tracked thread IDs when the mode is changed to none
            self.reply_thread_ids = set()

    @property
    def reply_verkeys(self):
        """Accessor for the reply verkeys."""
        return self._reply_verkeys.copy()

    @reply_verkeys.setter
    def reply_verkeys(self, verkeys: Sequence[str]):
        """Setter for the reply verkeys."""
        self._reply_verkeys = set(verkeys) if verkeys else set()

    @property
    def reply_thread_ids(self):
        """Accessor for the reply thread IDs."""
        return self._reply_thread_ids.copy()

    @reply_thread_ids.setter
    def reply_thread_ids(self, thread_ids: Sequence[str]):
        """Setter for the reply thread IDs."""
        self._reply_thread_ids = set(thread_ids) if thread_ids else set()

    def add_reply_thread_ids(self, *thids):
        """Add a thread ID to the set of potential reply targets."""
        for thid in filter(None, thids):
            self._reply_thread_ids.add(thid)

    def add_reply_verkeys(self, *verkeys):
        """Add a verkey to the set of potential reply targets."""
        for verkey in filter(None, verkeys):
            self._reply_verkeys.add(verkey)

    @property
    def response_buffered(self) -> bool:
        """Check if a response is currently buffered."""
        return bool(self.response_buffer)

    async def handle_relay_context(self, payload_enc: Union[str, bytes]):
        """Update the session profile based on the recipients of an incoming message."""
        multitenant_mgr = self.profile.context.inject(BaseMultitenantManager)

        try:
            [wallet] = await multitenant_mgr.get_wallets_by_message(
                payload_enc, self.wire_format
            )

            if wallet.is_managed:
                profile = await multitenant_mgr.get_wallet_profile(
                    self.profile.context, wallet
                )

                base_responder: AdminResponder = profile.inject(BaseResponder)

                # Create new responder based on base responder
                responder = AdminResponder(
                    profile,
                    base_responder.send_fn,
                )
                profile.context.injector.bind_instance(BaseResponder, responder)

                # overwrite session profile with wallet profile
                self.profile = profile

        except ValueError:
            pass  # No wallet found. Use the base session profile

    def process_inbound(self, message: InboundMessage):
        """
        Process an incoming message and update the session metadata as necessary.

        Args:
            message: The inbound message instance
        """
        receipt = message.receipt
        mode = self.reply_mode = (
            receipt.direct_response_requested and receipt.direct_response_mode
        )
        self.add_reply_verkeys(receipt.sender_verkey)
        if mode == MessageReceipt.REPLY_MODE_THREAD:
            self.add_reply_thread_ids(receipt.thread_id)

    async def parse_inbound(self, payload_enc: Union[str, bytes]) -> InboundMessage:
        """Convert a message payload and to an inbound message."""
        session = await self.profile.session()
        payload, receipt = await self.wire_format.parse_message(session, payload_enc)
        return InboundMessage(
            payload,
            receipt,
            session_id=self.session_id,
            transport_type=self.transport_type,
        )

    async def receive(self, payload_enc: Union[str, bytes]) -> InboundMessage:
        """Receive a new message payload and dispatch the message."""
        if self._check_relay_context:
            await self.handle_relay_context(payload_enc)
            self._check_relay_context = False

        message = await self.parse_inbound(payload_enc)
        self.receive_inbound(message)
        return message

    def receive_inbound(self, message: InboundMessage):
        """Deliver the inbound message to the conductor."""
        self.process_inbound(message)
        self.inbound_handler(self.profile, message, can_respond=self.can_respond)

    def select_outbound(self, message: OutboundMessage) -> bool:
        """Determine if an outbound message should be sent to this session.

        Args:
            message: The outbound message to be checked

        """
        if not self.can_respond:
            return False

        mode = self.reply_mode
        reply_verkey = message.reply_to_verkey
        reply_thread_id = message.reply_thread_id

        if reply_verkey and reply_verkey in self.reply_verkeys:
            if mode == MessageReceipt.REPLY_MODE_ALL:
                return True
            elif (
                mode == MessageReceipt.REPLY_MODE_THREAD
                and reply_thread_id
                and reply_thread_id in self._reply_thread_ids
            ):
                return True

        return False

    async def encode_outbound(self, outbound: OutboundMessage) -> OutboundMessage:
        """Apply wire formatting to an outbound message."""
        if not outbound.payload:
            raise WireFormatError("Message has no payload to encode")
        if not outbound.reply_to_verkey:
            raise WireFormatError("No reply verkey available for encoding message")

        session = await self.profile.session()
        return await self.wire_format.encode_message(
            session,
            outbound.payload,
            [outbound.reply_to_verkey],
            None,
            outbound.reply_from_verkey,
        )

    def accept_response(self, message: OutboundMessage) -> AcceptResult:
        """
        Try to queue an outbound message if it applies to this session.

        Returns: a tuple of (message buffered, retry later)
        """
        if not self.select_outbound(message):
            return AcceptResult(False, False)
        if self.response_buffer:
            return AcceptResult(False, True)
        self.set_response(message)
        return AcceptResult(True)

    def set_response(self, message: OutboundMessage):
        """Set the contents of the response message buffer."""
        self.response_buffer = message
        self.response_event.set()

    def clear_response(self):
        """Handle when the buffered response message has been delivered."""
        self.response_buffer = None
        self.response_event.set()

    async def wait_response(self) -> Union[str, bytes]:
        """Wait for a response to be buffered and pack it."""
        while True:
            if self._closed:
                return
            if self.response_buffer:
                response = self.response_buffer.enc_payload
                if not response:
                    try:
                        response = await self.encode_outbound(self.response_buffer)
                    except WireFormatError as e:
                        LOGGER.warning("Error encoding direct response: %s", str(e))
                        self.clear_response()
                if response:
                    return response
            self.response_event.clear()
            await self.response_event.wait()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_value, exc_tb):
        """Async context manager entry."""
        self.close()
