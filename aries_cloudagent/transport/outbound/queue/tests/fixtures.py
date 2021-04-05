from ..base import BaseOutboundQueue


class QueueClassNoBaseClass:
    pass


class QueueClassNoProtocol(BaseOutboundQueue):
    pass


class QueueClassValid(BaseOutboundQueue):
    protocol = "testprotocol"

    def enqueue_message(self, payload, endpoint):
        pass

    def push(self, key, message):
        pass

    def start(self):
        pass

    def stop(self):
        pass
