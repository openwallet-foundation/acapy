"""
The dispatcher is responsible for coordinating data flow between handlers, providing lifecycle hook callbacks
storing state for message threads, etc.
"""

import logging

from ..storage.base import BaseStorage


class Dispatcher:
    def __init__(self, storage: BaseStorage):
        self.logger = logging.getLogger(__name__)
        self.storage = storage

