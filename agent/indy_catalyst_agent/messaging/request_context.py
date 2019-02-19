"""
Request context class.

A request context provides everything required by handlers and other parts
of the system to process a message.
"""

import copy
import json
import logging
from typing import Union

from .agent_message import AgentMessage
from .message_factory import MessageFactory, MessageParseError
from ..models.connection_target import ConnectionTarget
from ..storage.base import BaseStorage
from ..wallet.base import BaseWallet
from ..wallet.error import WalletError, WalletNotFoundError


class RequestContext:
    """Context established by the Conductor and passed into message handlers."""

    def __init__(self):
        """Initialize an instance of RequestContext."""
        self._default_endpoint = None
        self._default_label = None
        self._logger = logging.getLogger(__name__)
        self._recipient_verkey = None
        self._recipient_did = None
        self._recipient_did_public = False
        self._sender_verkey = None
        self._transport_type = None
        self._message_factory = None
        self._message = None
        self._storage = None
        self._wallet = None

    def copy(self) -> "RequestContext":
        """
        Create a copy of this context.

        Returns:
            A copy of this instance

        """
        return copy.copy(self)

    @property
    def default_endpoint(self) -> str:
        """
        Accessor for the default agent endpoint (from agent config).

        Returns:
            The default agent endpoint

        """
        return self._default_endpoint

    @default_endpoint.setter
    def default_endpoint(self, endpoint: str):
        """
        Setter for the default agent endpoint (from agent config).

        Args:
            endpoint: The new default endpoint

        """
        self._default_endpoint = endpoint

    @property
    def default_label(self) -> str:
        """
        Accessor for the default agent label (from agent config).

        Returns:
            The default label

        """
        return self._default_label

    @default_label.setter
    def default_label(self, label: str):
        """
        Setter for the default agent label (from agent config).

        Args:
            label: The new default label

        """
        self._default_label = label

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
        Setter for the transport type used to receive the message

        Args:
            transport: This context's new transport

        """
        self._transport_type = transport

    @property
    def message_factory(self) -> MessageFactory:
        """
        Accessor for the message factory instance.

        Returns:
            This context's message factory

        """
        return self._message_factory

    @message_factory.setter
    def message_factory(self, factory: MessageFactory):
        """
        Setter for the message factory instance.

        Args:
            factory: This context's new message factory

        """
        self._message_factory = factory

    @property
    def message(self) -> AgentMessage:
        """
        Accessor for the deserialized message instance.

        Returns:
            This context's agent message

        """
        return self._message

    @message.setter
    def message(self, msg: AgentMessage):
        """
        Setter for the deserialized message instance.

        Args:
            msg: This context's new agent message
        """
        self._message = msg

    @property
    def storage(self) -> BaseStorage:
        """
        Accessor for the BaseStorage implementation.

        Returns:
            This context's storage implementation

        """
        return self._storage

    @storage.setter
    def storage(self, storage: BaseStorage):
        """
        Setter for the BaseStorage implementation.

        Args:
            storage: This context's new storage driver
        """
        self._storage = storage

    @property
    def wallet(self) -> BaseWallet:
        """
        Accessor for the BaseWallet implementation.

        Returns:
            This context's wallet implementation

        """
        return self._wallet

    @wallet.setter
    def wallet(self, wallet: BaseWallet):
        """
        Setter for the BaseWallet implementation.

        Args:
            wallet: This context's new wallet implementation
        """
        self._wallet = wallet

    async def expand_message(
        self, message_body: Union[str, bytes], transport_type: str
    ) -> "RequestContext":
        """
        Deserialize an incoming message.

        Args:
            message_body: The body of the incoming message
            transport_type: The transport type of this message

        Returns:
            The updated context

        Raises:
            MessageParseError: If there is no message factory on the context
            MessageParseError: If there is no wallet on the context
            MessageParseError: If contents of the message json cannot be parsed

        """
        if not self.message_factory:
            raise MessageParseError("Message factory not defined")
        if not self.wallet:
            raise MessageParseError("Wallet not defined")

        message_dict = None
        message_json = message_body
        from_verkey = None
        to_verkey = None

        if isinstance(message_body, bytes):
            try:
                message_json, from_verkey, to_verkey = await self.wallet.unpack_message(
                    message_body
                )
            except WalletError:
                self._logger.debug("Message unpack failed")

        try:
            message_dict = json.loads(message_json)
        except ValueError:
            raise MessageParseError("Message JSON parsing failed")
        self._logger.debug(f"Extracted message: {message_dict}")

        ctx = self.copy()
        ctx.message = self.message_factory.make_message(message_dict)
        ctx.transport_type = transport_type

        if from_verkey:
            ctx.sender_verkey = from_verkey

        if to_verkey:
            ctx.recipient_verkey = to_verkey
            try:
                did_info = await self.wallet.get_local_did_for_verkey(to_verkey)
            except WalletNotFoundError:
                did_info = None
            if did_info:
                ctx.recipient_did = did_info.did
            # TODO set ctx.recipient_did_public if DID is published to the ledger
            # could also choose to set ctx.default_endpoint and ctx.default_label
            # (these things could be stored on did_info.metadata)

        # look up existing thread and connection information, if any

        # handle any other decorators having special behaviour (timing, trace, etc)

        return ctx

    async def compact_message(
        self, message: AgentMessage, target: ConnectionTarget
    ) -> Union[str, bytes]:
        """
        Serialize an outgoing message for transport.

        Args:
            message: The agent message to serialize
            target: The connection target to compact for

        Returns:
            The serialized message

        """
        message_dict = message.serialize()
        message_json = json.dumps(message_dict)
        if target.sender_key and target.recipient_keys:
            message = await self.wallet.pack_message(
                message_json, target.recipient_keys, target.sender_key
            )
        else:
            message = message_json
        return message

    # Missing:
    # - NodePool
    # - Connection info / state
    # - Thread state
    # - Extra transport info? (received at endpoint?)

    def __repr__(self) -> str:
        """
        Provide a human readable representation of this object.

        Returns:
            A human readable representation of this object
        """
        skip = ("_logger",)
        items = (
            "{}={}".format(k, repr(v))
            for k, v in self.__dict__.items()
            if k not in skip
        )
        return "<{}({})>".format(self.__class__.__name__, ", ".join(items))
