"""
The timing decorator (~timing).

This decorator allows the timing of agent messages to be communicated
and constrained.
"""

from marshmallow import fields

from .base import BaseModel, BaseModelSchema

DT_FORMAT = "%Y-%m-%d %H:%M:%S.%fZ"


class TimingDecorator(BaseModel):
    """Class representing the timing decorator."""

    class Meta:
        """TimingDecorator metadata."""

        schema_class = "TimingDecoratorSchema"

    def __init__(
        self,
        *,
        in_time: str = None,
        out_time: str = None,
        stale_time: str = None,
        expires_time: str = None,
        delay_milli: int = None,
        wait_until_time: str = None,
    ):
        """
        Initialize a TimingDecorator instance.

        Args:
            in_time: The time the message was received
            out_time: The time the message was dispatched
            stale_time: When the message should be considered stale
            expires_time: When the message should be considered expired
            delay_milli: The number of milliseconds to delay processing
            wait_until_time: The earliest time at which to perform processing

        # TODO: accept datetime instances for dates
        """
        super(TimingDecorator, self).__init__()
        self.in_time = in_time
        self.out_time = out_time
        self.stale_time = stale_time
        self.expires_time = expires_time
        self.delay_milli = delay_milli
        self.wait_until_time = wait_until_time


class TimingDecoratorSchema(BaseModelSchema):
    """Timing decorator schema used in serialization/deserialization."""

    class Meta:
        """TimingDecoratorSchema metadata."""

        model_class = TimingDecorator

    in_time = fields.Date(format=DT_FORMAT, required=False)
    out_time = fields.Date(format=DT_FORMAT, required=False)
    stale_time = fields.Date(format=DT_FORMAT, required=False)
    expires_time = fields.Date(format=DT_FORMAT, required=False)
    delay_milli = fields.Int(required=False)
    wait_until_time = fields.Date(format=DT_FORMAT, required=False)
