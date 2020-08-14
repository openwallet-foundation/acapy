"""An object for containing updated route information."""

from marshmallow import EXCLUDE, fields

from .....messaging.models.base import BaseModel, BaseModelSchema


class RouteUpdated(BaseModel):
    """Class representing a route update response."""

    class Meta:
        """RouteUpdated metadata."""

        schema_class = "RouteUpdatedSchema"

    RESULT_CLIENT_ERROR = "client_error"
    RESULT_SERVER_ERROR = "server_error"
    RESULT_NO_CHANGE = "no_change"
    RESULT_SUCCESS = "success"

    def __init__(
        self,
        *,
        recipient_key: str = None,
        action: str = None,
        result: str = None,
        **kwargs
    ):
        """
        Initialize a RouteUpdated instance.

        Args:
            recipient_key: The recipient verkey of the route
            action: The requested action to perform
            result: The result of the requested action

        """
        super().__init__(**kwargs)
        self.recipient_key = recipient_key
        self.action = action
        self.result = result


class RouteUpdatedSchema(BaseModelSchema):
    """RouteUpdated schema."""

    class Meta:
        """RouteUpdatedSchema metadata."""

        model_class = RouteUpdated
        unknown = EXCLUDE

    recipient_key = fields.Str(required=True)
    action = fields.Str(required=True)
    result = fields.Str(required=True)
