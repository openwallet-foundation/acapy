import logging

from asyncio import Queue

from .base import BaseOutboundMessageQueue


class BasicOutboundMessageQueue(BaseOutboundMessageQueue):
    def __init__(self):
        self.queue = Queue()
        self.logger = logging.getLogger(__name__)

    async def enqueue(self, message):
        self.logger.debug(f"Enqueuing message: {message}")
        await self.queue.put(message)

    async def dequeue(self):
        message = await self.queue.get()
        self.logger.debug(f"Dequeuing message: {message}")
        return message

    def __aiter__(self):
        return self

    async def __anext__(self):
        message = await self.dequeue()
        return message
