"""
The dispatcher is responsible for coordinating data flow between handlers, providing lifecycle
hook callbacks storing state for message threads, etc.
"""

import logging

from .lifecycle import Lifecycle
from .storage.base import BaseStorage


class Dispatcher:
    def __init__(self, storage: BaseStorage):  # TODO: take in wallet impl as well
        self.logger = logging.getLogger(__name__)
        self.storage = storage

    def dispatch(self, message):
        # TODO:
        # Create an instance of some kind of "ThreadState" or "Context"
        # using a thread id found in the message data. Messages do not
        # yet have the notion of threading
        context = {}
        message.handler.handle(Lifecycle, context)

