"""An object for containing route information to be updated."""

from marshmallow import EXCLUDE, fields

from .....messaging.models.base import BaseModel, BaseModelSchema


class RouteUpdate(BaseModel):
    """Class representing a route update request."""

    class Meta:
        """RouteUpdate metadata."""

        schema_class = "RouteUpdateSchema"

    ACTION_CREATE = "create"
    ACTION_DELETE = "delete"

    def __init__(self, *, recipient_key: str = None, action: str = None, **kwargs):
        """
        Initialize a RouteUpdate instance.

        Args:
            recipient_key: The recipient verkey of the route
            action: The action to perform

        """
        super().__init__(**kwargs)
        self.recipient_key = recipient_key
        self.action = action


class RouteUpdateSchema(BaseModelSchema):
    """RouteUpdate schema."""

    class Meta:
        """RouteUpdateSchema metadata."""

        model_class = RouteUpdate
        unknown = EXCLUDE

    recipient_key = fields.Str(required=True)
    action = fields.Str(required=True)
