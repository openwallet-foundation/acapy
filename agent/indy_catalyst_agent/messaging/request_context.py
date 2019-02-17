"""
Request context class
"""

import copy
import logging

from .agent_message import AgentMessage
from .connections.models.connection_target import ConnectionTarget
from .message_factory import MessageFactory
from ..storage.base import BaseStorage
from ..wallet.base import BaseWallet


class RequestContext:
    """Context established by the Conductor and passed into message handlers"""

    def __init__(self):
        self._connection_active = False
        self._connection_target = None
        self._default_endpoint = None
        self._default_label = None
        self._logger = logging.getLogger(__name__)
        self._recipient_verkey = None
        self._recipient_did = None
        self._recipient_did_public = False
        self._sender_did = None
        self._sender_verkey = None
        self._transport_type = None
        self._message_factory = None
        self._message = None
        self._storage = None
        self._wallet = None

    def copy(self) -> "RequestContext":
        """Create a copy of this context"""
        return copy.copy(self)

    @property
    def connection_active(self) -> bool:
        """Accessor for the flag indicating an active connection with the sender"""
        return self._connection_active

    @connection_active.setter
    def connection_active(self, active: bool):
        """Setter for the flag indicating an active connection with the sender

        :param active: bool:

        """
        self._connection_active = active

    @property
    def connection_target(self) -> ConnectionTarget:
        """Accessor for the ConnectionTarget associated with the current connection"""
        return self._connection_target

    @connection_target.setter
    def connection_target(self, target: ConnectionTarget):
        """Setter for the ConnectionTarget associated with the current connection

        :param target: str:

        """
        self._connection_target = target

    @property
    def default_endpoint(self) -> str:
        """Accessor for the default agent endpoint (from agent config)"""
        return self._default_endpoint

    @default_endpoint.setter
    def default_endpoint(self, endp: str):
        """Setter for the default agent endpoint (from agent config)

        :param endp: str:

        """
        self._default_endpoint = endp

    @property
    def default_label(self) -> str:
        """Accessor for the default agent label (from agent config)"""
        return self._default_label

    @default_label.setter
    def default_label(self, lbl: str):
        """Setter for the default agent label (from agent config)

        :param lbl: str:

        """
        self._default_label = lbl

    @property
    def recipient_verkey(self) -> str:
        """Accessor for the recipient public key used to pack the incoming request"""
        return self._recipient_verkey

    @recipient_verkey.setter
    def recipient_verkey(self, verkey: str):
        """Setter for the recipient public key used to pack the incoming request

        :param verkey: str:

        """
        self._recipient_verkey = verkey

    @property
    def recipient_did(self) -> str:
        """Accessor for the recipient DID which corresponds with the verkey"""
        return self._recipient_did

    @recipient_did.setter
    def recipient_did(self, did: str):
        """Setter for the recipient DID which corresponds with the verkey

        :param did: str:

        """
        self._recipient_did = did

    @property
    def recipient_did_public(self) -> bool:
        """
        Indicates whether the message is associated with a public (ledger) recipient DID
        """
        return self._recipient_did_public

    @recipient_did_public.setter
    def recipient_did_public(self, public: bool):
        """Setter for the flag indicating the recipient DID is public

        :param public: bool:

        """
        self._recipient_did_public = public

    @recipient_verkey.setter
    def recipient_verkey(self, verkey: str):
        """Setter for the recipient public key used to pack the incoming request

        :param verkey: str:

        """
        self._recipient_verkey = verkey

    @property
    def sender_did(self) -> str:
        """Accessor for the sender DID which corresponds with the verkey"""
        return self._sender_did

    @sender_did.setter
    def sender_did(self, did: str):
        """Setter for the sender DID which corresponds with the verkey

        :param did: str:

        """
        self._sender_did = did

    @property
    def sender_verkey(self) -> str:
        """Accessor for the sender public key used to pack the incoming request"""
        return self._sender_verkey

    @sender_verkey.setter
    def sender_verkey(self, verkey: str):
        """Setter for the sender public key used to pack the incoming request

        :param verkey: str:

        """
        self._sender_verkey = verkey

    @property
    def transport_type(self) -> str:
        """Accessor for the transport type used to receive the message"""
        return self._transport_type

    @transport_type.setter
    def transport_type(self, transport: str):
        """Setter for the transport type used to receive the message

        :param transport: str:

        """
        self._transport_type = transport

    @property
    def message_factory(self) -> MessageFactory:
        """Accessor for the message factory instance"""
        return self._message_factory

    @message_factory.setter
    def message_factory(self, factory: MessageFactory):
        """Setter for the message factory instance

        :param factory: MessageFactory:

        """
        self._message_factory = factory

    @property
    def message(self) -> AgentMessage:
        """Accessor for the deserialized message instance"""
        return self._message

    @message.setter
    def message(self, msg: AgentMessage):
        """Setter for the deserialized message instance

        :param msg: AgentMessage:

        """
        self._message = msg

    @property
    def storage(self) -> BaseStorage:
        """Accessor for the BaseStorage implementation"""
        return self._storage

    @storage.setter
    def storage(self, storage: BaseStorage):
        """Setter for the BaseStorage implementation

        :param storage: BaseStorage:

        """
        self._storage = storage

    @property
    def wallet(self) -> BaseWallet:
        """Accessor for the BaseWallet implementation"""
        return self._wallet

    @wallet.setter
    def wallet(self, wallet: BaseWallet):
        """Setter for the BaseWallet implementation

        :param wallet: BaseWallet:
        """
        self._wallet = wallet

    # Missing:
    # - NodePool
    # - Connection info / state
    # - Thread state
    # - Extra transport info? (received at endpoint?)

    def __repr__(self) -> str:
        skip = ("_logger",)
        items = (
            "{}={}".format(k, repr(v))
            for k, v in self.__dict__.items()
            if k not in skip
        )
        return "<{}({})>".format(self.__class__.__name__, ", ".join(items))
