"""The timing decorator (~timing) allows the timing of agent messages
to be communicated and constrained
"""

from typing import Sequence

from marshmallow import fields

from .base import BaseModel, BaseModelSchema

DT_FORMAT = "%Y-%m-%d %H:%M:%S.%fZ"


class TimingDecorator(BaseModel):
    """Class representing the timing decorator."""

    class Meta:
        schema_class = "TimingDecoratorSchema"

    def __init__(
        self,
        *,
        locale: str = None,
        localizable: Sequence[str] = None,
        catalogs: Sequence[str] = None,
    ):
        super(TimingDecorator, self).__init__()
        self.locale = locale
        self.localizable = list(localizable) if localizable else []
        self.catalogs = list(catalogs) if catalogs else []


class TimingDecoratorSchema(BaseModelSchema):
    """Timing decorator schema used in serialization/deserialization"""

    class Meta:
        model_class = TimingDecorator

    in_time = fields.Date(format=DT_FORMAT, required=False)
    out_time = fields.Date(format=DT_FORMAT, required=False)
    stale_time = fields.Date(format=DT_FORMAT, required=False)
    expires_time = fields.Date(format=DT_FORMAT, required=False)
    delay_milli = fields.Int(required=False)
    wait_until_time = fields.Date(format=DT_FORMAT, required=False)
