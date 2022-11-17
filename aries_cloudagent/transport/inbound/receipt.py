"""Classes for representing message receipt details."""

from datetime import datetime
from typing import Optional


class MessageReceipt:
    """Properties of an agent message's delivery."""

    # TODO - add trust context information

    REPLY_MODE_ALL = "all"
    REPLY_MODE_NONE = "none"
    REPLY_MODE_THREAD = "thread"

    def __init__(
        self,
        *,
        connection_id: str = None,
        direct_response_mode: str = None,
        in_time: datetime = None,
        raw_message: str = None,
        recipient_verkey: str = None,
        recipient_did: str = None,
        recipient_did_public: bool = None,
        sender_did: str = None,
        sender_verkey: str = None,
        thread_id: str = None,
        parent_thread_id: str = None,
    ):
        """Initialize the message delivery instance."""
        self._connection_id = connection_id
        self._direct_response_mode = direct_response_mode
        self._in_time = in_time
        self._raw_message = raw_message
        self._recipient_verkey = recipient_verkey
        self._recipient_did = recipient_did
        self._recipient_did_public = recipient_did_public
        self._sender_did = sender_did
        self._sender_verkey = sender_verkey
        self._thread_id = thread_id
        self._parent_thread_id = parent_thread_id

    @property
    def connection_id(self) -> str:
        """
        Accessor for the pairwise connection identifier.

        Returns:
            This context's connection identifier

        """
        return self._connection_id

    @connection_id.setter
    def connection_id(self, connection_id: bool):
        """
        Setter for the pairwise connection identifier.

        Args:
            connection_id: This context's new connection identifier

        """
        self._connection_id = connection_id

    @property
    def direct_response_mode(self) -> str:
        """
        Accessor for the requested direct response mode.

        Returns:
            This context's requested direct response mode

        """
        return self._direct_response_mode

    @direct_response_mode.setter
    def direct_response_mode(self, mode: str) -> str:
        """Setter for the requested direct response mode."""
        self._direct_response_mode = mode

    @property
    def direct_response_requested(self) -> str:
        """
        Accessor for the the state of the direct response mode.

        Returns:
            This context's requested direct response mode

        """
        return self._direct_response_mode and self._direct_response_mode != "none"

    @property
    def in_time(self) -> str:
        """
        Accessor for the datetime the message was received.

        Returns:
            This context's received time

        """
        return self._in_time

    @in_time.setter
    def in_time(self, in_time: datetime):
        """
        Setter for the datetime the message was received.

        Args:
            in_time: This context's new received time

        """
        self._in_time = in_time

    @property
    def raw_message(self) -> str:
        """
        Accessor for the raw message text.

        Returns:
            The raw message text

        """
        return self._raw_message

    @raw_message.setter
    def raw_message(self, message: str):
        """
        Setter for the raw message text.

        Args:
            message: The new message text

        """
        self._raw_message = message

    @property
    def recipient_did(self) -> str:
        """
        Accessor for the recipient DID which corresponds with the verkey.

        Returns:
            The recipient DID

        """
        return self._recipient_did

    @recipient_did.setter
    def recipient_did(self, did: str):
        """
        Setter for the recipient DID which corresponds with the verkey.

        Args:
            did: The new recipient DID

        """
        self._recipient_did = did

    @property
    def recipient_did_public(self) -> bool:
        """
        Check if the recipient did is public.

        Indicates whether the message is associated with
        a public (ledger) recipient DID.

        Returns:
            True if the recipient's DID is public, else false

        """
        return self._recipient_did_public

    @recipient_did_public.setter
    def recipient_did_public(self, public: bool):
        """
        Setter for the flag indicating the recipient DID is public.

        Args:
            public: A boolean value to indicate if the recipient DID is public

        """
        self._recipient_did_public = public

    @property
    def recipient_verkey(self) -> str:
        """
        Accessor for the recipient verkey key used to pack the incoming request.

        Returns:
            The recipient verkey

        """
        return self._recipient_verkey

    @recipient_verkey.setter
    def recipient_verkey(self, verkey: str):
        """
        Setter for the recipient public key used to pack the incoming request.

        Args:
            verkey: This context's recipient's verkey

        """
        self._recipient_verkey = verkey

    @property
    def sender_did(self) -> str:
        """
        Accessor for the sender DID which corresponds with the verkey.

        Returns:
            The sender did

        """
        return self._sender_did

    @sender_did.setter
    def sender_did(self, did: str):
        """
        Setter for the sender DID which corresponds with the verkey.

        Args:
            The new sender did

        """
        self._sender_did = did

    @property
    def sender_verkey(self) -> str:
        """
        Accessor for the sender public key used to pack the incoming request.

        Returns:
            This context's sender's verkey

        """
        return self._sender_verkey

    @sender_verkey.setter
    def sender_verkey(self, verkey: str):
        """
        Setter for the sender public key used to pack the incoming request.

        Args:
            verkey: This context's sender's verkey

        """
        self._sender_verkey = verkey

    @property
    def thread_id(self) -> str:
        """
        Accessor for the identifier of the message thread.

        Returns:
            The delivery thread ID

        """
        return self._thread_id

    @thread_id.setter
    def thread_id(self, thread: str):
        """
        Setter for the message thread identifier.

        Args:
            thread: The new thread identifier

        """
        self._thread_id = thread

    @property
    def parent_thread_id(self) -> Optional[str]:
        """
        Accessor for the identifier of the message parent thread.

        Returns:
            The delivery parent thread ID

        """
        return self._parent_thread_id

    @parent_thread_id.setter
    def parent_thread_id(self, thread: Optional[str]):
        """
        Setter for the message parent thread identifier.

        Args:
            thread: The new parent thread identifier

        """
        self._parent_thread_id = thread

    def __repr__(self) -> str:
        """
        Provide a human readable representation of this object.

        Returns:
            A human readable representation of this object

        """
        items = ("{}={}".format(k, repr(v)) for k, v in self.__dict__.items())
        return "<{}({})>".format(self.__class__.__name__, ", ".join(items))
