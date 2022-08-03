"""Inner structure of keylist-update-response.

Represents single item in keylist-update-response.updated list.
"""

from marshmallow import EXCLUDE, fields

from ......messaging.models.base import BaseModel, BaseModelSchema
from ......messaging.valid import DID_KEY
from ......did.did_key import DIDKey
from ......wallet.key_type import KeyType


class KeylistUpdated(BaseModel):
    """Class representing a route update response."""

    class Meta:
        """KeylistUpdated metadata."""

        schema_class = "KeylistUpdatedSchema"

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
        Initialize a KeylistUpdated instance.

        Args:
            recipient_key: The recipient verkey of the route
            action: The requested action to perform
            result: The result of the requested action

        """
        super().__init__(**kwargs)
        if recipient_key.startswith("did:key:"):
            self.recipient_key = recipient_key
        else:
            self.recipient_key = (
                DIDKey.from_public_key_b58(recipient_key, KeyType.ED25519).did
            )
        self.action = action
        self.result = result


class KeylistUpdatedSchema(BaseModelSchema):
    """KeylistUpdated schema."""

    class Meta:
        """KeylistUpdatedSchema metadata."""

        model_class = KeylistUpdated
        unknown = EXCLUDE

    recipient_key = fields.Str(required=True, **DID_KEY)
    action = fields.Str(required=True)
    result = fields.Str(required=True)
