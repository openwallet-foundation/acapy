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
    def __init__(self, parsed_transports: list) -> None:
        self.logger = logging.getLogger(__name__)
        self.transports = parsed_transports

    async def start(self) -> None:
        # TODO: make storage type configurable via cli params
        storage = BasicStorage()
        self.dispatcher = Dispatcher(storage)

        for transport in self.transports:
            if transport["transport"] == "http":
                transport = HttpTransport(
                    transport["host"], transport["port"], self.message_handler
                )
                await transport.start()
            else:
                raise InvalidTransportError()

    def message_handler(self, message_dict: dict) -> None:
        message = MessageFactory.make_message(message_dict)
        self.dispatcher.dispatch(message)
