"""
The Delivery Queue.

The delivery queue holds and manages messages that have not yet
been delivered to their intended destination.

"""
from aries_cloudagent.messaging.outbound_message import OutboundMessage


class DeliveryQueue:
    """
    Conductor class.


    """

    def __init__(self) -> None:
        """
        Initialize an instance of DeliveryQueue.


        """

        self.queue_by_key = {}

    def add_message(self, msg:OutboundMessage):
        for recipient_key in msg.target.recipient_keys:
            if recipient_key not in self.queue_by_key:
                self.queue_by_key[recipient_key] = []
            self.queue_by_key[recipient_key].append(msg)

    def has_message_for_key(self, key:str):
        return key in self.queue_by_key and len(self.queue_by_key[key])

    def get_one_message_for_key(self, key):
        return self.queue_by_key[key].pop(0)

    def inspect_all_messages_for_key(self, key:str):
        return self.queue_by_key[key]

    def remove_message_for_key(self, key, undelivered_message):
        self.queue_by_key[key].remove(undelivered_message)