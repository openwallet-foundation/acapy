"""Inner structure of keylist message. Represents a single item in keylist.keys."""

from marshmallow import EXCLUDE, fields

from ......messaging.models.base import BaseModel, BaseModelSchema
from ......messaging.valid import INDY_RAW_PUBLIC_KEY, DID_KEY
from ......did.did_key import DIDKey
from ......wallet.key_type import KeyType


class KeylistKey(BaseModel):
    """Inner structure of Keylist keys attribute."""

    class Meta:
        """KeylistKey metadata."""

        schema_class = "KeylistKeySchema"

    def __init__(
        self,
        *,
        recipient_key: str = None,
        action: str = None,
        result: str = None,
        **kwargs
    ):
        """
        Initialize a KeylistKey instance.

        Args:
            recipient_key: The recipient verkey of the route
            action: The requested action to perform
            result: The result of the requested action

        """
        super().__init__(**kwargs)
        if recipient_key.startswith("did:key:"):
            self.recipient_key = recipient_key
        else:
            self.recipient_key = DIDKey.from_public_key_b58(recipient_key, KeyType.ED25519).did


class KeylistKeySchema(BaseModelSchema):
    """KeylistKey schema."""

    class Meta:
        """KeylistKeySchema metadata."""

        model_class = KeylistKey
        unknown = EXCLUDE

    recipient_key = fields.Str(required=True, **DID_KEY)
