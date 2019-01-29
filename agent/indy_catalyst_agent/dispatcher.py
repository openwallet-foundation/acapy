"""
The dispatcher is responsible for coordinating data flow between handlers, providing lifecycle
hook callbacks storing state for message threads, etc.
"""

import logging

from .storage.base import BaseStorage
from .messaging.agent_message import AgentMessage
from .transport.outbound.message import OutboundMessage
from .connection import Connection


class Dispatcher:
    def __init__(self, storage: BaseStorage):  # TODO: take in wallet impl as well
        self.logger = logging.getLogger(__name__)
        self.storage = storage

    async def dispatch(self, message: AgentMessage, send):
        # TODO:
        # Create an instance of some kind of "ThreadState" or "Context"
        # using a thread id found in the message data. Messages do not
        # yet have the notion of threading
        context = {}

        # Create "connection"

        # pack/unpack

        message.handler.handle(context)

        # 1. get handler result
        # 1a. Possibly communicate with service backend for instructions
        # 2. based on some logic, build a response message

        handler_response = message  # echo for now

        # conn = Connection(endpoint="wss://0bc6628c.ngrok.io")
        conn1 = Connection(endpoint="http://25566605.ngrok.io")
        conn2 = Connection(endpoint="https://httpbin.org/status/400")

        # Potentially multicast to multiple 
        await send(handler_response, conn1)
        await send(handler_response, conn2)


        # We also return the result to the caller.
        # This is for persistent connections waiting on that response.
        return handler_response

        # await send(OutboundMessage(uri="https://httpbin.org/status/200", data=None))
        # await send(OutboundMessage(uri="https://httpbin.org/status/200", data=None))

        # await connection.send_message(handler_response)

