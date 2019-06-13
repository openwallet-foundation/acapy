"""
The transport decorator (~transport).

This decorator allows changes to agent response behaviour and queue status updates.
"""

from marshmallow import fields

from ..models.base import BaseModel, BaseModelSchema


class TransportDecorator(BaseModel):
    """Class representing the transport decorator."""

    class Meta:
        """TransportDecorator metadata."""

        schema_class = "TransportDecoratorSchema"

    def __init__(
        self,
        *,
        return_route: str = None,
        return_route_thread: str = None,
        queued_message_count: int = None,
    ):
        """
        Initialize a TransportDecorator instance.

        Args:
            return_route: Set the return routing mode
            return_route_thread: Identify the thread to enable return routing for
            queued_message_count: Indicate the number of queued messages
        """
        super(TransportDecorator, self).__init__()
        self.return_route = return_route
        self.return_route_thread = return_route_thread
        self.queued_message_count = queued_message_count


class TransportDecoratorSchema(BaseModelSchema):
    """Transport decorator schema used in serialization/deserialization."""

    class Meta:
        """TransportDecoratorSchema metadata."""

        model_class = TransportDecorator

    return_route = fields.Str(required=False)
    return_route_thread = fields.Str(required=False)
    queued_message_count = fields.Int(required=False)
