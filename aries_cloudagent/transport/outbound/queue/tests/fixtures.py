from ..base import BaseOutboundQueue


class QueueClassNoBaseClass:
    def __init__(self, settings):
        pass


class QueueClassValid(BaseOutboundQueue):
    async def enqueue_message(self, payload, endpoint):
        pass

    async def push(self, key, message):
        pass

    async def start(self):
        pass

    async def stop(self):
        pass
