"""Classes for representing message delivery details."""

from datetime import datetime


class MessageDelivery:
    """Properties of an agent message's delivery."""

    # TODO - add trust context information

    def __init__(
        self,
        *,
        direct_response: bool = False,
        in_time: datetime = None,
        recipient_verkey: str = None,
        recipient_did: str = None,
        recipient_did_public: str = None,
        sender_did: str = None,
        sender_verkey: str = None,
        transport_type: str = None,
    ):
        """Initialize the message delivery instance."""
        self._direct_response = direct_response
        self._in_time = in_time
        self._recipient_verkey = recipient_verkey
        self._recipient_did = recipient_did
        self._recipient_did_public = recipient_did_public
        self._sender_did = sender_did
        self._sender_verkey = sender_verkey
        self._transport_type = transport_type

    @property
    def direct_response(self) -> str:
        """
        Accessor for the flag indicating that direct responses are preferred.

        Returns:
            This context's direct response flag

        """
        return self._direct_response

    @direct_response.setter
    def direct_response(self, direct: bool):
        """
        Setter for the flag indicating that direct responses are preferred.

        Args:
            transport: This context's new direct response flag

        """
        self._direct_response = direct

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
            transport: This context's new received time

        """
        self._in_time = in_time

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
            verkey: The new recipient verkey
        """
        self._recipient_verkey = verkey

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
    def transport_type(self) -> str:
        """
        Accessor for the transport type used to receive the message.

        Returns:
            This context's transport type

        """
        return self._transport_type

    @transport_type.setter
    def transport_type(self, transport: str):
        """
        Setter for the transport type used to receive the message.

        Args:
            transport: This context's new transport

        """
        self._transport_type = transport

    def __repr__(self) -> str:
        """
        Provide a human readable representation of this object.

        Returns:
            A human readable representation of this object

        """
        skip = ()
        items = (
            "{}={}".format(k, repr(v))
            for k, v in self.__dict__.items()
            if k not in skip
        )
        return "<{}({})>".format(self.__class__.__name__, ", ".join(items))
