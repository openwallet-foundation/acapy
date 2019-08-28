"""
The Delivery Queue.

The delivery queue holds and manages messages that have not yet
been delivered to their intended destination.

"""
import time

from aries_cloudagent.messaging.outbound_message import OutboundMessage


class QueuedMessage:
    """
    Wrapper Class for queued messages.

    Allows tracking Metadata.
    """

    def __init__(self, msg: OutboundMessage):
        """
        Create Wrapper for queued message.

        Automatically sets timestamp on create.
        """
        self.msg = msg
        self.timestamp = time.time()

    def older_than(self, compare_timestamp):
        """
        Age Comparison.

        Allows you to test age as compared to the provided timestamp.
        :param compare_timestamp:
        :return:
        """
        return self.timestamp < compare_timestamp


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
        self.ttl_seconds = 604800  # one week

    def expire_messages(self, ttl=None):
        """
        Expire messages that are past the time limit.

        :param ttl: Optional. Allows override of configured ttl
        :return: None
        """

        ttl_seconds = ttl or self.ttl_seconds
        horizon = time.time() - ttl_seconds
        for key in self.queue_by_key.keys():
            self.queue_by_key[key] = [wm for
                                      wm in self.queue_by_key[key]
                                      if not wm.older_than(horizon)]

    def add_message(self, msg: OutboundMessage):
        """
        Add an OutboundMessage to delivery queue.

        The message is added once per recipient key

        Arguments:
            msg: The OutboundMessage to add
        """
        wrapped_msg = QueuedMessage(msg)
        for recipient_key in msg.target.recipient_keys:
            if recipient_key not in self.queue_by_key:
                self.queue_by_key[recipient_key] = []
            self.queue_by_key[recipient_key].append(wrapped_msg)

    def has_message_for_key(self, key: str):
        """
        Check for queued messages by key.

        Arguments:
            key: The key to use for lookup
        """
        if key in self.queue_by_key and len(self.queue_by_key[key]):
            return True
        return False

    def message_count_for_key(self, key: str):
        """
        Count of queued messages by key.

        Arguments:
            key: The key to use for lookup
        """
        if key in self.queue_by_key:
            return len(self.queue_by_key[key])
        else:
            return 0

    def get_one_message_for_key(self, key: str):
        """
        Remove and return a matching message.

        Arguments:
            key: The key to use for lookup
        """
        return self.queue_by_key[key].pop(0).msg

    def inspect_all_messages_for_key(self, key: str):
        """
        Return all messages for key.

        Arguments:
            key: The key to use for lookup
        """
        for wrapped_msg in self.queue_by_key[key]:
            yield wrapped_msg.msg

    def remove_message_for_key(self, key, msg: OutboundMessage):
        """
        Remove specified message from queue for key.

        Arguments:
            key: The key to use for lookup
            msg: The message to remove from the queue
        """
        for wrapped_msg in self.queue_by_key[key]:
            if wrapped_msg.msg == msg:
                self.queue_by_key[key].remove(wrapped_msg)
                break  # exit processing loop
