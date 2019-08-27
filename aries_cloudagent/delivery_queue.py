"""
The Delivery Queue.

The delivery queue holds and manages messages that have not yet
been delivered to their intended destination.

"""
from aries_cloudagent.messaging.outbound_message import OutboundMessage


class DeliveryQueue:
    """
    DeliveryQueue class.

    Manages undelivered messages.
    """

    def __init__(self) -> None:
        """
        Initialize an instance of DeliveryQueue.

        This uses an in memory structure to queue messages.
        """

        self.queue_by_key = {}

    def add_message(self, msg: OutboundMessage):
        """
        Add an OutboundMessage to delivery queue.

        The message is added once per recipient key

        Arguments:
            msg: The OutboundMessage to add
        """
        for recipient_key in msg.target.recipient_keys:
            if recipient_key not in self.queue_by_key:
                self.queue_by_key[recipient_key] = []
            self.queue_by_key[recipient_key].append(msg)

    def has_message_for_key(self, key: str):
        """
        Check for queued messages by key.

        Arguments:
            key: The key to use for lookup
        """
        if key in self.queue_by_key and len(self.queue_by_key[key]):
            return True
        return False

    def get_one_message_for_key(self, key: str):
        """
        Remove and return a matching message.

        Arguments:
            key: The key to use for lookup
        """
        return self.queue_by_key[key].pop(0)

    def inspect_all_messages_for_key(self, key: str):
        """
        Return all messages for key.

        Arguments:
            key: The key to use for lookup
        """
        return self.queue_by_key[key]

    def remove_message_for_key(self, key, msg: OutboundMessage):
        """
        Remove specified message from queue for key.

        Arguments:
            key: The key to use for lookup
            msg: The message to remove from the queue
        """
        self.queue_by_key[key].remove(msg)
