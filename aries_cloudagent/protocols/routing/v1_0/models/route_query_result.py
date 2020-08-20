"""An object for containing returned route information."""

from marshmallow import EXCLUDE, fields

from .....messaging.models.base import BaseModel, BaseModelSchema


class RouteQueryResult(BaseModel):
    """Class representing route information returned by a route query."""

    class Meta:
        """RouteQueryResult metadata."""

        schema_class = "RouteQueryResultSchema"

    def __init__(self, *, recipient_key: str = None, **kwargs):
        """
        Initialize a RouteQueryResult instance.

        Args:
            recipient_key: The recipient verkey of the route

        """
        super().__init__(**kwargs)
        self.recipient_key = recipient_key


class RouteQueryResultSchema(BaseModelSchema):
    """RouteQueryResult schema."""

    class Meta:
        """RouteQueryResultSchema metadata."""

        model_class = RouteQueryResult
        unknown = EXCLUDE

    recipient_key = fields.Str(required=True)
