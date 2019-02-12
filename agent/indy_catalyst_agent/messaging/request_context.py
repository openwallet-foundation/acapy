"""
Request context class
"""

import copy

from .agent_message import AgentMessage
from ..storage import BaseStorage
from ..wallet import BaseWallet


class RequestContext:
    """
    Context established by Dispatcher and passed into message handlers
    """

    def __init__(self):
        self._default_endpoint = None
        self._default_label = None
        self._recipient_verkey = None
        self._sender_verkey = None
        self._transport_type = None
        self._message = None
        self._storage = None
        self._wallet = None

    def copy(self) -> 'RequestContext':
        """
        Create a copy of this context
        """
        return copy.copy(self)

    @property
    def default_endpoint(self) -> str:
        """
        Accessor for the default agent endpoint (from agent config)
        """
        return self._default_endpoint

    @default_endpoint.setter
    def default_endpoint(self, endp: str):
        """
        Setter for the default agent endpoint (from agent config)
        """
        self._default_endpoint = endp

    @property
    def default_label(self) -> str:
        """
        Accessor for the default agent label (from agent config)
        """
        return self._default_label

    @default_label.setter
    def default_label(self, lbl: str):
        """
        Setter for the default agent label (from agent config)
        """
        self._default_label = lbl

    @property
    def recipient_verkey(self) -> str:
        """
        Accessor for the recipient public key used to pack the incoming request
        """
        return self._recipient_verkey

    @recipient_verkey.setter
    def recipient_verkey(self, verkey: str):
        """
        Setter for the recipient public key used to pack the incoming request
        """
        self._recipient_verkey = verkey

    @property
    def sender_verkey(self) -> str:
        """
        Accessor for the sender public key used to pack the incoming request
        """
        return self._sender_verkey

    @sender_verkey.setter
    def sender_verkey(self, verkey: str):
        """
        Setter for the sender public key used to pack the incoming request
        """
        self._sender_verkey = verkey

    @property
    def transport_type(self) -> str:
        """
        Accessor for the transport type used to receive the message
        """
        return self._transport_type

    @transport_type.setter
    def transport_type(self, transport: str):
        """
        Setter for the transport type used to receive the message
        """
        self._transport_type = transport
    
    @property
    def message(self) -> AgentMessage:
        """
        Accessor for the deserialized message instance
        """
        return self._message

    @message.setter
    def message(self, msg: AgentMessage):
        """
        Setter for the deserialized message instance
        """
        self._message = msg

    @property
    def storage(self) -> BaseStorage:
        """
        Accessor for the BaseStorage implementation
        """
        return self._storage

    @storage.setter
    def storage(self, storage: BaseStorage):
        """
        Setter for the BaseStorage implementation
        """
        self._storage = storage

    @property
    def wallet(self) -> BaseWallet:
        """
        Accessor for the BaseWallet implementation
        """
        return self._wallet

    @wallet.setter
    def wallet(self, wallet: BaseWallet):
        """
        Setter for the BaseWallet implementation
        """
        self._wallet = wallet


    # Missing:
    # - NodePool
    # - Connection info / state
    # - Thread state
    # - Extra transport info? (received at endpoint?)

    def __repr__(self) -> str:
        items = ("{}={}".format(k, repr(v)) for k, v in self.__dict__.items())
        return "<{}({})>".format(self.__class__.__name__, ', '.join(items))
