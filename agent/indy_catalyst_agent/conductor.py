"""
The conductor is responsible for coordinating messages that are received
over the network, communicating with the ledger, passing messages to handlers,
and storing data in the wallet.
"""

import logging

from .dispatcher import Dispatcher

from .transport.http import Http as HttpTransport
from .transport import InvalidTransportError

from .storage.basic import BasicStorage

from .messaging.message_factory import MessageFactory


class Conductor:
    def __init__(self, transport: str, host: str, port: int) -> None:
        self.logger = logging.getLogger(__name__)
        self.transport = transport
        self.host = host
        self.port = port

    def start(self) -> None:
        # TODO: make storage type configurable via cli params
        storage = BasicStorage()
        self.dispatcher = Dispatcher(storage)

        if self.transport is "http":
            transport = HttpTransport(self.host, self.port, self.message_handler)
            transport.setup()
        else:
            raise InvalidTransportError()

    def message_handler(self, message_dict: dict) -> None:
        message = MessageFactory.make_message(message_dict)
        self.dispatcher.dispatch(message)
