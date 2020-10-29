"""
A message decorator for threads.

A thread decorator identifies a message that may require additional
context from previous messages.
"""

from typing import Mapping

from marshmallow import EXCLUDE, fields

from ..models.base import BaseModel, BaseModelSchema
from ..valid import UUIDFour


class ThreadDecorator(BaseModel):
    """Class representing thread decorator."""

    class Meta:
        """ThreadDecorator metadata."""

        schema_class = "ThreadDecoratorSchema"

    def __init__(
        self,
        *,
        thid: str = None,
        pthid: str = None,
        sender_order: int = None,
        received_orders: Mapping = None,
    ):
        """
        Initialize a ThreadDecorator instance.

        Args:
            thid: The ID of the message that serves as the
                thread start
            pthid: An optional parent thid. Used when branching
                or nesting a new interaction off of an existing one.
            sender_order:A number that tells where this message
                fits in the sequence of all messages that the
                current sender has contributed to this thread
            received_orders: Reports the highest sender_order value
                that the sender has seen from other sender(s) on the
                thread. (This value is often missing if it is the first
                message in an interaction, but should be used otherwise,
                as it provides an implicit ACK.)

        """
        super().__init__()
        self._thid = thid
        self._pthid = pthid
        self._sender_order = sender_order or None
        self._received_orders = received_orders and dict(received_orders) or None

    @property
    def thid(self):
        """
        Accessor for thread identifier.

        Returns:
            This thread's `thid`

        """
        return self._thid

    @property
    def pthid(self):
        """
        Accessor for parent thread identifier.

        Returns:
            This thread's `pthid`

        """
        return self._pthid

    @pthid.setter
    def pthid(self, val: str):
        """
        Setter for parent thread identifier.

        Args:
            val: The new pthid
        """
        self._pthid = val

    @property
    def received_orders(self) -> dict:
        """
        Get received orders.

        Returns:
            The highest sender_order value that the sender has seen from other
            sender(s) on the thread.

        """
        return self._received_orders

    @property
    def sender_order(self) -> int:
        """
        Get sender order.

        Returns:
            A number that tells where this message fits in the sequence of all
            messages that the current sender has contributed to this thread

        """
        return self._sender_order


class ThreadDecoratorSchema(BaseModelSchema):
    """Thread decorator schema used in serialization/deserialization."""

    class Meta:
        """ThreadDecoratorSchema metadata."""

        model_class = ThreadDecorator
        unknown = EXCLUDE

    thid = fields.Str(
        required=False,
        allow_none=True,
        description="Thread identifier",
        example=UUIDFour.EXAMPLE,  # typically a UUID4 but not necessarily
    )
    pthid = fields.Str(
        required=False,
        allow_none=True,
        description="Parent thread identifier",
        example=UUIDFour.EXAMPLE,  # typically a UUID4 but not necessarily
    )
    sender_order = fields.Int(
        required=False,
        allow_none=True,
        description="Ordinal of message among all from current sender in thread",
        example=11,
        strict=True,
    )
    received_orders = fields.Dict(
        keys=fields.Str(description="Sender key"),
        values=fields.Int(
            description="Highest sender_order value for sender",
            example=3,
            strict=True,
        ),
        required=False,
        allow_none=True,
        description=(
            "Highest sender_order value that sender has seen from others on thread"
        ),
    )
