"""An object for containing information on an individual route."""

from marshmallow import fields

from ....messaging.models.base import BaseModel, BaseModelSchema


class RouteRecord(BaseModel):
    """Class representing stored route information."""

    class Meta:
        """RouteRecord metadata."""

        schema_class = "RouteRecordSchema"

    def __init__(
        self,
        *,
        record_id: str = None,
        connection_id: str = None,
        recipient_key: str = None,
        created_at: str = None,
        updated_at: str = None,
        **kwargs
    ):
        """
        Initialize a RouteRecord instance.

        Args:
            recipient_key: The recipient verkey of the route

        """
        super(RouteRecord, self).__init__(**kwargs)
        self.record_id = record_id
        self.connection_id = connection_id
        self.recipient_key = recipient_key
        self.created_at = created_at
        self.updated_at = updated_at


class RouteRecordSchema(BaseModelSchema):
    """RouteRecord schema."""

    class Meta:
        """RouteRecordSchema metadata."""

        model_class = "RouteRecord"

    record_id = fields.Str(required=False)
    connection_id = fields.Str(required=True)
    recipient_key = fields.Str(required=True)
    created_at = fields.Str(required=False)
    updated_at = fields.Str(required=False)
