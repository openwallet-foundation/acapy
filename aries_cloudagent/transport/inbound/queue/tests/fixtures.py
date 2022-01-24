from ..base import BaseInboundQueue


class QueueClassNoBaseClass:
    def __init__(self, settings):
        pass


class QueueClassValid(BaseInboundQueue):
    async def receive_message(self):
        pass

    async def push(self, key, message):
        pass

    async def start(self):
        pass

    async def stop(self):
        pass
