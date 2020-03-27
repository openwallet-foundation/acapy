"""A keylist update rule inner object."""

from marshmallow import fields
from marshmallow.validate import OneOf

from .....messaging.models.base import BaseModel, BaseModelSchema
from .....messaging.valid import INDY_RAW_PUBLIC_KEY


class KeylistUpdateResult(BaseModel):
    """Class representing a keylist update result."""

    class Meta:
        """Keylist update result metadata."""

        schema_class = "KeylistUpdateResultSchema"

    RULE_ADD = "add"
    RULE_REMOVE = "remove"

    RESULT_CLIENT_ERROR = "client_error"
    RESULT_SERVER_ERROR = "server_error"
    RESULT_NO_CHANGE = "no_change"
    RESULT_SUCCESS = "success"

    def __init__(
        self,
        recipient_key: str,
        action: str,
        result: str = None,
        **kwargs
    ):
        """
        Initialize keylist update result object.

        Args:
            recipient_key: recipient key for the rule
            action: action for the rule
            result: result of the update

        """
        super().__init__(**kwargs)
        self.recipient_key = recipient_key
        self.action = action
        self.result = result


class KeylistUpdateResultSchema(BaseModelSchema):
    """Keylist update result specifiation schema."""

    class Meta:
        """Keylist update result schema metadata."""

        model_class = KeylistUpdateResult

    recipient_key = fields.Str(
        description="Keylist to remove or add",
        required=True,
        **INDY_RAW_PUBLIC_KEY
    )
    action = fields.Str(
        required=False,
        description="Action for specific key",
        example=KeylistUpdateResult.RULE_ADD,
        validate=OneOf(["add", "remove"]),
    )
    result = fields.Str(
        required=False,
        description="Result of the action for specific key",
        example=KeylistUpdateResult.RESULT_NO_CHANGE,
        validate=OneOf(["client_error", "server_error", "no_change", "success"]),
    )
